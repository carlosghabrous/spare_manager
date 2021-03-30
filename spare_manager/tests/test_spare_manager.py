"""
High-level tests for the  package.

"""
import fgc
import pyfgc
import spare_manager
from spare_manager import config_blender

import cx_Oracle
import pytest
from pathlib import Path

DB_USER = 'pocontrols_mod'
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

_db_conn_strings = {'dev': DEV_DSN, 'pro': PRO_DSN}


def test_version():
    assert spare_manager.__version__ is not None

@pytest.mark.parametrize('operational, spare', [
    # ('RPAGM.866.04.ETH8', 'RPAAO.866.02.ETH8'),
    ('RFMAG.866.19.ETH1', 'RFNA.866.04.ETH1')
])
def test_properties_correctly_set_in_db(operational, spare):
    db_instance = 'pro'

    with open(Path(PWD_DIR) / db_instance.lower() / DB_USER.lower()) as pfh:
        secret = pfh.read().rstrip()

    with cx_Oracle.connect(DB_USER, secret, _db_conn_strings[db_instance.lower()]) as db_connection:
        with db_connection.cursor() as cursor:
            operational_properties = config_blender._get_system_properties(operational, cursor)
            spare_properties = config_blender._get_system_properties(spare, cursor)

            combo = operational + '_' + str(operational_properties['DEVICE.SPARE_ID'].value)
            combo_properties = config_blender._get_system_properties(combo, cursor)

    assert operational_properties.keys() == spare_properties.keys()
    assert operational_properties.keys() == combo_properties.keys()

    for p in operational_properties.keys():
        try:
            fgc.properties.fgc_properties[p]['from_spare_converter']

        except KeyError:
            assert combo_properties[p] == operational_properties[p]

        else:
            assert combo_properties[p] == spare_properties[p]

    with pyfgc.fgc(operational) as combo_fgc:
        for p in combo_properties.keys():
            fgc_value = combo_fgc.get(p).value
            db_value = combo_properties[p].value

            try:
                assert fgc_value == db_value

            except AssertionError:
                # Cope with values' differences such as 04 and 4
                try:
                    assert int(fgc_value) == int(db_value)

                except AssertionError:
                    raise AssertionError(f'Assertion error on property {p}; fgc value: {fgc_value}; db: {db_value}')

