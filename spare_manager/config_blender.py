"""Creates configuration for an operational-spare combination.

The script gets the operational and spare devices as arguments. It retrieves from the 
configuration tables the system properties for each one and mixes them in a new set of
system properties. The script uses the fgc/properties.py module to know which properties
to take from the operational and spare systems, respectively, looking at the property
argument 'from_spare_converter=1'.
"""
import argparse
import sys
from collections import namedtuple
from pathlib import Path

import cx_Oracle

import pyfgc_name
from fgc import properties


DB_USER = "POCONTROLS_MOD"
PWD_DIR = '/user/pclhc/etc/program_manager/private/'

DEV_DSN = '''(DESCRIPTION=
            (ADDRESS=(PROTOCOL=TCP)(HOST=devdb18-s.cern.ch)(PORT=10121))
            (ENABLE=BROKEN)
            (CONNECT_DATA = (SERVICE_NAME = devdb18_s.cern.ch)))
            '''
            
PRO_DSN = '''(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=acccon-s.cern.ch)(PORT=10121))
           (ENABLE=BROKEN)
           (CONNECT_DATA = (SERVICE_NAME = acccon_s.cern.ch)))
           '''

UPDATE_DEVICE_SPARE_ID = '''
UPDATE FGC_SYSTEM_PROPERTIES fsp
SET SPR_VALUE=:spare_id
WHERE SPR_ID=(
  SELECT 
    fsp.SPR_ID 
  FROM 
    FGC_SYSTEM_PROPERTIES fsp 
  INNER JOIN FGC_SYSTEMS fs 
  ON fs.SYS_ID = fsp.SPR_SYS_ID 
  INNER JOIN FGC_PROPERTIES fp 
  ON fp.PRO_ID = fsp.SPR_PRO_ID 
  WHERE 
    fs.SYS_NAME=:operational_sys_name AND 
    fp.PRO_NAME=:property_name)
'''

INSERT_COMBO_SYSTEM = '''
INSERT INTO FGC_SYSTEMS fs
(SYS_NAME, SYS_TP_ID, SYS_CLASS_ID, SYS_IS_OBSOLETE, SYS_IS_SPARE_COMBINATION)
(SELECT
  :combo_sys_name,
  fs.SYS_TP_ID,
  :class_id,
  0,
  1
FROM
  FGC_SYSTEMS fs 
WHERE 
  fs.SYS_NAME=:spare_sys_name)
'''

GET_SPARE_SYS_ID = '''
SELECT 
  fs.SYS_ID 
FROM 
  FGC_SYSTEMS fs 
WHERE
  fs.SYS_NAME=:combo_sys_name
'''

LINK_SPARE_COMPONENTS_TO_COMBO_SYSTEM = '''
INSERT INTO 
FGC_COMPONENT_SYSTEMS fcs
(fcs.CS_SYS_ID, fcs.CS_CMP_ID)
SELECT 
  (SELECT 
    fs.SYS_ID 
  FROM 
    FGC_SYSTEMS fs 
  WHERE 
    fs.sys_name=:combo_sys_name) AS SYS_ID,
    fcs.CS_CMP_ID
FROM 
  FGC_COMPONENT_SYSTEMS fcs 
INNER JOIN FGC_SYSTEMS fs 
ON fs.SYS_ID = fcs.CS_SYS_ID
INNER JOIN FGC_COMPONENTS fc 
ON fc.CMP_ID = fcs.CS_CMP_ID
WHERE 
  fs.SYS_NAME=:spare_sys_name
'''

GET_SYSTEM_PROPERTIES = '''
SELECT 
  fp.PRO_NAME, 
  fp.PRO_ID,
  fsp.SPR_VALUE 
FROM 
  FGC_PROPERTIES fp
INNER JOIN FGC_SYSTEM_PROPERTIES fsp 
ON fp.PRO_ID = fsp.SPR_PRO_ID
INNER JOIN FGC_SYSTEMS fs 
ON fs.SYS_ID = fsp.SPR_SYS_ID 
WHERE 
  fs.SYS_NAME=:system_name
'''

DELETE_COMPONENTS_FROM_COMBO_SYSTEM = '''
DELETE 
FROM 
FGC_COMPONENT_SYSTEMS fcs
WHERE
  fcs.CS_SYS_ID = (
SELECT 
  fs.SYS_ID 
FROM 
  FGC_SYSTEMS fs 
WHERE 
  fs.SYS_NAME=:combo_sys_name)
'''

DELETE_COMBO_SYSTEM = '''
DELETE FROM FGC_SYSTEMS WHERE sys_name=:combo_sys_name
'''

DELETE_SYSTEM_PROPERTIES_COMBO = '''
DELETE FROM FGC_SYSTEM_PROPERTIES fsp
WHERE 
  fsp.SPR_SYS_ID = (SELECT fs.SYS_ID from FGC_SYSTEMS fs WHERE fs.SYS_NAME=:combo_sys_name)
'''

INSTANTIATE_SYSTEM_PROPERTIES = '''
INSERT INTO FGC_SYSTEM_PROPERTIES
(SPR_SYS_ID, SPR_PRO_ID, SPR_VALUE)
VALUES
(:1, :2, :3)
'''

GET_SPARE_SYSTEMS = '''
SELECT
  fs.SYS_NAME
FROM 
  FGC_SYSTEMS fs 
WHERE 
  fs.SYS_IS_SPARE_COMBINATION = 1
ORDER BY 
  fs.SYS_NAME ASC
'''

GET_SYSTEM_ID = '''
SELECT
  fs.SYS_ID
FROM 
  FGC_SYSTEMS fs
WHERE 
  fs.SYS_NAME=:system_name
'''

_db_conn_strings = {'dev': DEV_DSN, 'pro': PRO_DSN}

def _get_db_crendentials(db_instance):
    with open(Path(PWD_DIR) / db_instance.lower() / DB_USER.lower()) as pfh:
        secret = pfh.read().rstrip()

    return secret

def _delete_components_from_combo_system(combo_sys_name, cursor):
    cursor.execute(DELETE_COMPONENTS_FROM_COMBO_SYSTEM, {'combo_sys_name':combo_sys_name})
    
def _delete_combo_system(combo_sys_name, cursor):
    cursor.execute(DELETE_COMBO_SYSTEM, {'combo_sys_name': combo_sys_name})
    
def _delete_system_properties_from_combo_system(combo_sys_name, cursor):
    cursor.execute(DELETE_SYSTEM_PROPERTIES_COMBO, {'combo_sys_name':combo_sys_name})

def _reset_device_spare_id_in_operational(operational_sys_name, cursor):
    data_update = {'spare_id':'0', 'operational_sys_name':operational_sys_name, 'property_name':'DEVICE.SPARE_ID'}
    cursor.execute(UPDATE_DEVICE_SPARE_ID, data_update)

def _get_system_properties(system_name, cursor):
    Property = namedtuple('Property', 'id, name, value')
    system_properties = dict()
    
    data_get = {'system_name':system_name}
    for prop_name, prop_id, prop_value in cursor.execute(GET_SYSTEM_PROPERTIES, data_get):
        p = Property(prop_id, str(prop_name), str(prop_value))
        system_properties[prop_name] = p
        
    return system_properties
    
def _instantiate_system_properties(operational_sys_name, spare_sys_name, combo_sys_name, sys_id, cursor):
    op_system_properties    = _get_system_properties(operational_sys_name, cursor)
    spare_system_properties = _get_system_properties(spare_sys_name, cursor)

    op_properties    = sorted(op_system_properties.keys())
    spare_properties = sorted(spare_system_properties.keys())
    try:
        assert op_properties == spare_properties

    except AssertionError as ae:
        msg = 'ERROR: system properties for operational and spare systems are not the same!\n'
        msg += f'Operational: {op_properties};\n Spare: {spare_properties}\n'
        msg += f'Difference: {set(op_properties) ^ set(spare_properties)}'
        raise AssertionError(msg) from ae

    combo_system_properties = dict()
    for prop in op_system_properties.keys():
        try:
            properties.fgc_properties[prop]

        except KeyError:
            print(f'ERROR: system property {prop} not found in properties.py autogenerated module! Make sure module and database are in sync')
            continue

        try:
            properties.fgc_properties[prop]['from_spare_converter']

        except KeyError:
            combo_system_properties[prop] = op_system_properties[prop]

        else:
            combo_system_properties[prop] = spare_system_properties[prop]

    data = list()
    for _, p in combo_system_properties.items():
        data.append((sys_id, p.id, p.value))

    cursor.executemany(INSTANTIATE_SYSTEM_PROPERTIES, data)
    
def _link_spare_components_to_new_system(combo_sys_name, spare_sys_name, cursor):
    cursor.execute(LINK_SPARE_COMPONENTS_TO_COMBO_SYSTEM, {'combo_sys_name':combo_sys_name, 'spare_sys_name':spare_sys_name})

def _insert_combo_system(spare, combo_system_name, cursor):
    cursor.execute(INSERT_COMBO_SYSTEM, {'combo_sys_name': combo_system_name, 'class_id': pyfgc_name.devices[spare]['class_id'], 'spare_sys_name': spare})
    cursor.execute(GET_SPARE_SYS_ID, {'combo_sys_name': combo_system_name})
    new_sys_id = cursor.fetchone()[0]
    return new_sys_id

def _generate_combo_system_name(operational, spare):
    spare_id = '{:02d}'.format(pyfgc_name.devices[spare]['channel'])
    combo_system_name = operational + '_' + spare_id
    return combo_system_name

def _get_combo_systems(db_instance: str):
    secret = _get_db_crendentials(db_instance)
    
    combo_systems = list()
    
    with cx_Oracle.connect(DB_USER, secret, _db_conn_strings[db_instance.lower()]) as db_connection:
        with db_connection.cursor() as cursor:
            combo_systems = [system_name[0] for system_name in cursor.execute(GET_SPARE_SYSTEMS).fetchall()]

    return combo_systems

def activate_configuration(combo_system_name, db_instance):
    operational_sys_name, spare_id = combo_system_name.split('_')
    secret = _get_db_crendentials(db_instance)

    with cx_Oracle.connect(DB_USER, secret, _db_conn_strings[db_instance.lower()]) as db_connection:
        db_connection.autocommit = False

        with db_connection.cursor() as cursor:
            data_update = {'spare_id':spare_id, 'operational_sys_name':operational_sys_name, 'property_name':'DEVICE.SPARE_ID'}
            cursor.execute(UPDATE_DEVICE_SPARE_ID, data_update)

        db_connection.commit()

def deactivate_configuration(combo_system_name, db_instance):
    operational_sys_name = combo_system_name.split('_')[0]
    secret = _get_db_crendentials(db_instance)

    with cx_Oracle.connect(DB_USER, secret, _db_conn_strings[db_instance.lower()]) as db_connection:
        db_connection.autocommit = False

        with db_connection.cursor() as cursor:
            _reset_device_spare_id_in_operational(operational_sys_name, cursor)

        db_connection.commit()

def delete_combo_system(operational: str, spare: str, db_instance: str):
    combo_sys_name = operational + '_' + '{:02d}'.format(pyfgc_name.devices[spare]['channel'])
    secret = _get_db_crendentials(db_instance)
    
    with cx_Oracle.connect(DB_USER, secret, _db_conn_strings[db_instance.lower()]) as db_connection:
        db_connection.autocommit = False

        with db_connection.cursor() as cursor:
            _delete_components_from_combo_system(combo_sys_name, cursor)
            _delete_system_properties_from_combo_system(combo_sys_name, cursor)
            _delete_combo_system(combo_sys_name, cursor)
            _reset_device_spare_id_in_operational(operational, cursor)

        db_connection.commit()

def get_system_id(combo_system_name: str, db_instance:str) -> int:
    secret = _get_db_crendentials(db_instance)
    system_id = None

    with cx_Oracle.connect(DB_USER, secret, _db_conn_strings[db_instance.lower()]) as db_connection:
        with db_connection.cursor() as cursor:
            system_id = cursor.execute(GET_SYSTEM_ID, {'system_name':combo_system_name}).fetchone()[0]

    return system_id

def get_spare_systems_from_operational(operational, db_instance):
    combo_systems = _get_combo_systems(db_instance)
    combo_systems_dongles = [int(dev.split('_')[-1]) for dev in combo_systems]
    spares = [spare for spare in pyfgc_name.gateways[operational.gateway]['devices'] if pyfgc_name.devices[spare]['channel'] in combo_systems_dongles]
    return spares

def _get_arguments_from_cmd_line(operational=None, spare=None, database=None):
    try:
        op_name = operational.pop()
        spare_name = spare.pop()
        db_instance = database.pop()
    
    except TypeError:
        print('Wrong input arguments!')
        sys.exit(2)

    else:
        return op_name, spare_name, db_instance

def run_security_checks(operational: str, spare: str, db_instance:str) -> None:
    if operational == spare:
        raise AssertionError(f'Operational and spare devices cannot be the same!')

    op_class_id    = pyfgc_name.devices[operational]['class_id']
    spare_class_id = pyfgc_name.devices[spare]['class_id']
    if op_class_id != spare_class_id:
        raise AssertionError(f'FGCs {operational} and {spare} are of different classes!')

    op_gw    = pyfgc_name.devices[operational]['gateway']
    spare_gw = pyfgc_name.devices[spare]['gateway']
    if op_gw != spare_gw:
        raise AssertionError(f'FGCs {operational} and {spare} belong to different gateways!')

    try:
        _db_conn_strings[db_instance.lower()]
    
    except KeyError as ke:
        possible_values = ', '.join([k for k in _db_conn_strings.keys()])
        raise KeyError(f'Database instance {db_instance} not valid! Possible values: {possible_values}') from ke

def create_op_spare_combo_system(operational: str, spare: str, db_instance: str) -> int:
    new_sys_id = None

    run_security_checks(operational, spare, db_instance)
    secret = _get_db_crendentials(db_instance)
    combo_system_name = _generate_combo_system_name(operational, spare)

    with cx_Oracle.connect(DB_USER, secret, _db_conn_strings[db_instance.lower()]) as db_connection:
        db_connection.autocommit = False

        with db_connection.cursor() as cursor:
            try:
                _reset_device_spare_id_in_operational(operational, cursor)
                new_sys_id = _insert_combo_system(spare, combo_system_name, cursor)
                _link_spare_components_to_new_system(combo_system_name, spare, cursor)
                _instantiate_system_properties(operational, spare, combo_system_name, new_sys_id, cursor)
                db_connection.commit()

            except cx_Oracle.Error as oe:
                raise RuntimeError(str(oe))

    return new_sys_id

def configure_parser(parser: 'argparser.ArgumentParser') -> None:
    parser.description = __doc__

    parser.add_argument('operational', metavar='OPERATIONAL FGC',   type=str, nargs=1, help='Operational FGC3')
    parser.add_argument('spare',       metavar='SPARE FGC',         type=str, nargs=1, help='Spare FGC3')
    parser.add_argument('database',    metavar='DATABASE',          type=str, nargs=1, help='PRO(duction) or DEV(evelopment) database')
    parser.add_argument('--del',
                        dest='action',
                        action='store_const',
                        const=delete_combo_system,
                        default=create_op_spare_combo_system,
                        help='DELETE op-spare configuration (default: create op-spare configuration)')

if __name__ == '__main__':
    pyfgc_name.read_name_file()
    parser = argparse.ArgumentParser()
    configure_parser(parser)
    args = parser.parse_args().__dict__.copy()
    args.pop('action')(*_get_arguments_from_cmd_line(**args))
