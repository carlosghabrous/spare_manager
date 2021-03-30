import logging
import random
import time
import webbrowser
from collections import namedtuple
from pathlib     import Path

from PyQt5           import uic
from PyQt5.QtWidgets import QMainWindow, QWidget
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import (QComboBox,
                            QGroupBox,
                            QLabel,
                            QLineEdit,
                            QMessageBox,
                            QPlainTextEdit,
                            QProgressBar,
                            QPushButton,
                            QScrollArea)

from spare_manager import config_blender as blender
from spare_manager.model import SpareModel

DB_INSTANCE = 'pro'
DeviceData = namedtuple('DeviceData', 'name, class_id, gateway, dongle')

class QPlainTextEditLogger(logging.Handler):
    def __init__(self, parent, activityPlainTextEdit):
        super().__init__()
        self.plainTextEdit = activityPlainTextEdit
        self.plainTextEdit.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.plainTextEdit.appendPlainText(msg)
        self.plainTextEdit.verticalScrollBar().setValue(self.plainTextEdit.verticalScrollBar().maximum())

    def write(self, m):
        pass

class SpareManagerWindow(QMainWindow):
    """Spare manager main window.

    Arguments:
        QMainWindow {[type]} -- [description]
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self._display_config_logger = None
        self.ui = uic.loadUi(Path(__file__).parent / 'activate_config_view.ui', self)
        self._model = SpareModel()
        self.ui.operationalfgcComboBox.setModel(self._model)

        self._op_device = None
        self._spare_device = None
        self._combo_name = None
        self._set_signals_slots()

        self.setWindowTitle('Spare system manager - Existing configurations')
        self.show()

        logging.info('Spare management GUI ready')

    def _set_signals_slots(self):
        self.ui.operationalfgcPushButton.clicked.connect(lambda: self._load_device(self.ui.operationalfgcComboBox.currentText(), 'operational'))
        self.ui.sparefgcPushButton.clicked.connect(lambda: self._load_device(self.ui.relatedsparesComboBox.currentText(), 'spare'))
        self.ui.activateconfigPushButton.clicked.connect(lambda: self._activate_configuration(self._combo_name))
        self.ui.deactivateconfigPushButton.clicked.connect(lambda: self._deactivate_configuration(self._combo_name))
        self.ui.deleteconfigPushButton.clicked.connect(lambda: self._delete_combo_system(self._combo_name))

        self._create_activity_box()

    def _create_activity_box(self):        
        self._display_config_logger = QPlainTextEditLogger(self.ui.displayconfigScrollArea, self.ui.displayconfigPlainTextEdit)
        self._display_config_logger.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s]: %(message)s'))

        logging.getLogger().addHandler(self._display_config_logger)
        logging.getLogger().setLevel(logging.INFO)

    def _load_device(self, device, device_role):
        device_upper = device.upper()

        if device_role == 'operational':
            class_id, gw, dongle = self._model.getDeviceData(device)
            self._op_device = DeviceData(device, class_id, gw, dongle)
            self._update_existing_configs_dropbox()
            logging.info(f'FGC {device_upper} loaded as OPERATIONAL')

        elif device_role == 'spare' and self._op_device:
            class_id, gw, dongle = self._model.getDeviceData(device)
            self._spare_device = DeviceData(device, class_id, gw, dongle)
            logging.info(f'FGC {device_upper} loaded as OPERATIONAL')
            self._combo_name = self._op_device.name + '_' + '{:02d}'.format(self._spare_device.dongle)
            self._display_configuration(self._combo_name)

    def _update_existing_configs_dropbox(self):
        self.ui.relatedsparesComboBox.clear()

        try:
            spares = blender.get_spare_systems_from_operational(self._op_device, DB_INSTANCE)
            spares.sort()
            self.ui.relatedsparesComboBox.addItems(spares)
        
        except FileNotFoundError as fe:
            self._show_error_popup_window(str(fe))
            logging.info(f'Could not load spare systems that have been combined with the operational FGC! {fe}')

    def _delete_combo_system(self, system_combo_name):
        if not system_combo_name:
            msg = 'Cannot delete empty operational-spare combination'
            self._show_error_popup_window(msg)
            logging.info(msg)
            return

        op, spare = self._model.getOpAndSpareFromCombo(system_combo_name)

        try:
            blender.delete_combo_system(op, spare, DB_INSTANCE)

        except (KeyError, FileNotFoundError) as e:
            self._show_error_popup_window(str(e))

        else:
            time.sleep(1)
            logging.info('Operational-spare configuration successfully deleted')
            self._update_existing_configs_dropbox()
    
    def _display_configuration(self, system_combo_name):
        if not system_combo_name:
            msg = 'Cannot delete empty operational-spare combination'
            self._show_error_popup_window(msg)
            logging.info(msg)
            return

        system_id = blender.get_system_id(system_combo_name, DB_INSTANCE)
        if isinstance(system_id, int):
            logging.info(f'Link to the property manager: \nhttps://accwww.cern.ch/fgc_property_manager/details/system?id={system_id}')

        else:
            logging.error(f'Could not get system id for system: {system_combo_name}')

    def _activate_configuration(self, system_combo_name):
        if not system_combo_name:
            msg = 'Cannot activate empty operational-spare combination'
            self._show_error_popup_window(msg)
            logging.info(msg)
            return

        try:
            blender.activate_configuration(system_combo_name, DB_INSTANCE)        
        
        except Exception as e:
            self._show_error_popup_window(str(e))

        else:
            logging.info(f'Configuration {system_combo_name} has been activated')

    def _deactivate_configuration(self, system_combo_name):
        if not system_combo_name:
            msg = 'Cannot deactivate empty operational-spare combination'
            self._show_error_popup_window(msg)
            logging.info(msg)
            return

        try:
            blender.deactivate_configuration(system_combo_name, DB_INSTANCE)        
        
        except Exception as e:
            self._show_error_popup_window(str(e))

        else:
            logging.info(f'Configuration {system_combo_name} has been deactivated')

    def _show_error_popup_window(self, message):
        msg = QMessageBox()
        msg.setWindowTitle('This is not good...')
        msg.setText(message)
        _ = msg.exec_()

# EOF