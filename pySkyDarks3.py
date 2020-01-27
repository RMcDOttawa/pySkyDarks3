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

# Data model for this application.  If we were given a file name as an argument,
# load the data model from that file.  If not, create a new data model with default
# values as recorded in the application preferences

# sys.argv is a list. The first item is the application name, so there needs to be
# a second item for it to be a file name

# print(f"Called with args: {sys.argv}")

if len(sys.argv) >= 2:
    file_name = sys.argv[1]
    # print(f"  Using file name: {file_name}")
    data_model = DataModel.make_from_file_named(file_name)
    if data_model is None:
        print(f"Unable to read data model from file {file_name}")
        sys.exit(100)
else:
    data_model = DataModel()
    if data_model is None:
        print(f"Unable to create data model from preferences")
        sys.exit(101)

window = MainWindow()
window.accept_data_model(data_model)
window.ui.show()

app.exec_()

