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

        self._op_device = None
        self._spare_device = None
        self._generate_config_logger = None
        self._model = SpareModel()

        self.ui = uic.loadUi(Path(__file__).parent / 'create_config_view.ui', self)

        self._set_signals_slots()

        self.setWindowTitle('Spare system management - Create configuration')
        self.show()

        logging.info('Spare management GUI ready')

    def _set_signals_slots(self):
        # Generate Config tab
        self.ui.selectopdevicePushButton.clicked.connect(lambda: self._load_device(self.ui.operationalLineEdit.text(), 'operational'))
        self.ui.selectsparedevicePushButton.clicked.connect(lambda: self._load_device(self.ui.spareLineEdit.text(), 'spare'))
        self.ui.generatePushButton.clicked.connect(self._generate_config)

        self._create_activity_box()

    def _create_activity_box(self):        
        self._generate_config_logger = QPlainTextEditLogger(self.ui.activityGenerateScrollArea, self.ui.activityGeneratePlainTextEdit)
        self._generate_config_logger.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s]: %(message)s'))

        logging.getLogger().addHandler(self._generate_config_logger)
        logging.getLogger().setLevel(logging.INFO)

    def _load_device(self, device, device_role):
        device_upper = device.upper()

        try: 
            class_id, gw, dongle = self._model.getDeviceData(device_upper)

        except KeyError:
            self._show_error_popup_window(f'Sorry, but device {device} does not exist! Try again with a complete name!')
        
        else:
            if device_role == 'operational':
                self._op_device = DeviceData(device_upper, class_id, gw, dongle)
                logging.info(f'FGC {device_upper} loaded as OPERATIONAL')

            elif device_role == 'spare':
                self._spare_device = DeviceData(device_upper, class_id, gw, dongle)
                logging.info(f'FGC {device_upper} loaded as SPARE')

    def _generate_config(self):
        logging.info('Generating operational-spare configuration...')

        try:
            if self._op_device is None:
                raise AssertionError(f'Operational device has not been selected')

            if self._spare_device is None:
                raise AssertionError(f'Spare device has not been selected')

            system_id = blender.create_op_spare_combo_system(self._op_device.name, self._spare_device.name, DB_INSTANCE)
        
        except (AssertionError, FileNotFoundError, RuntimeError) as e:
            self._show_error_popup_window(str(e))
            logging.info(f'Operational-spare configuration could not be generated! {e}')

        else:
            time.sleep(1)
            logging.info('Operational-spare configuration successfully generated')
            logging.info(f'Link to the property manager: \nhttps://accwww.cern.ch/fgc_property_manager/details/system?id={system_id}')
            self._clean()

    def _clean(self):
        self._op_device = None
        self._spare_device = None

    def _show_error_popup_window(self, message):
        msg = QMessageBox()
        msg.setWindowTitle('This is not good...')
        msg.setText(message)
        _ = msg.exec_()

# EOF