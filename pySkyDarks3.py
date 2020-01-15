import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import QCoreApplication

from DataModel import DataModel
from MainWindow import MainWindow

app = QtWidgets.QApplication(sys.argv)

# Set organization info to allow un-parameterized QSettings constructor
QCoreApplication.setOrganizationName("EarwigHavenObservatory")
QCoreApplication.setOrganizationDomain("earwighavenobservatory.com")
QCoreApplication.setApplicationName("pySkyDarks2")
QCoreApplication.setApplicationVersion("1.0")
# Preferences are stored with the following keys
#       last_opened_path        The last file opened or saved, so next can go to same place

window = MainWindow()
dataModel = DataModel()
window.accept_data_model(dataModel)
window.ui.show()

app.exec_()

