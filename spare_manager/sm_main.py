'''
Usage sm_main [-c|-a]
Options:
    -c: Launches the GUI to create a spare-operational configuration
    -a: Launches the GUI to activate a spare-operational configuration already created
'''

import importlib
import sys
from PyQt5.QtWidgets import QApplication

__options_to_gui_module = {'-c': 'spare_manager.create_configuration', 
                            '-a': 'spare_manager.activate_configuration'}
try:
    option = sys.argv[1]

except IndexError:
    print(f'Missing option! {__doc__}')
    sys.exit(2)

if option not in ['-c', '-a']:
    print(f'Invalid option! Available options: {__doc__}')
    sys.exit(2)


# import spare_manager.view
try:
    gui_module = importlib.import_module(__options_to_gui_module[option])

except ImportError:
    print(f'Could not import module {__options_to_gui_module[option]}')
    sys.exit(1)

app = QApplication(list())
app.setStyle('Oxygen')
spare_manager = gui_module.SpareManagerWindow()
sys.exit(app.exec_())
# EOF