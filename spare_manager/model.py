import re
from PyQt5 import QtCore

import pyfgc_name

try:
    pyfgc_name.read_name_file(filename='/Users/cghabrou/Code/cern/name')

except FileNotFoundError:
    pyfgc_name.read_name_file()

class SpareModel(QtCore.QAbstractListModel):
    def __init__(self, *args, devices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_devices = [dev for dev, dev_obj in pyfgc_name.devices.items() if dev_obj['class_id'] == 63]
        self.devices = devices if devices else self.default_devices
        self.devices.sort()

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid() is False:
            return QtCore.QVariant()

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.ItemDataRole:
            try:
                text = self.devices[index.row()]
            
            except IndexError:
                pass
            
            else:
                return text

    def rowCount(self, index):
        return len(self.devices)

    def rebuildDeviceList(self, dev_filter_str):
        dev_filter_str_uc = dev_filter_str.upper()
        filtered_devices = [dev for dev in self.default_devices if re.search(dev_filter_str_uc, dev)]
        
        for row, _ in enumerate(self.devices):
            self.beginRemoveRows(QtCore.QModelIndex(), row, row)
            self.endRemoveRows()
        
        self.devices = filtered_devices

    def getDeviceData(self, device_name):
        dev_obj = pyfgc_name.devices[device_name]
        return dev_obj['class_id'], dev_obj['gateway'], dev_obj['channel']

    def getOpAndSpareFromCombo(self, combo_name):
        operational, spare_id = combo_name.split('_')
        spare_dongle = int(spare_id)
        fgcs_same_gw = pyfgc_name.gateways[pyfgc_name.devices[operational]['gateway']]['devices']

        for fgc in fgcs_same_gw:
            dongle_id = pyfgc_name.devices[fgc]['channel']
        
            if int(dongle_id) == spare_dongle:
                return operational, fgc
        
        else:
            return operational, ''
                
# EOF
