
#   The following method variables are accessible via getters.  No setters - no external setting.
#   _numBiasFrames      number of bias frames for each of the following binnings
#   _biasBinnings       array of binning values for bias frames.  empty if none
#   _numDarkFrames      number of dark frames for each binning and exposure
#   _darkBinnings       array of binning values for dark frames, empty if none
#   _darkExposures      array of exposure values (float, seconds) for dark frames
import re

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog

from Validators import Validators


class BulkEntryDialog(QDialog):

    def getNumBiasFrames(self) -> int:
        return self._numBiasFrames

    def getBiasBinnings(self) -> [int]:
        return self._biasBinnings

    def getNumDarkFrames(self) -> int:
        return self._numDarkFrames

    def getDarkBinnings(self) -> [int]:
        return self._darkBinnings

    def getDarkExposures(self) -> [int]:
        return self._darkExposures

    def __init__(self):
        # print("BulkEntryDialog/init entered")
        QDialog.__init__(self)
        self.ui = uic.loadUi("BulkEntry.ui")

        self._numBiasFrames: int = 0
        self._numDarkFrames: int = 0
        self._darkExposures: [float] = []
        self._biasBinnings: [int] = []
        self._darkBinnings: [int] = []

        self.setBiasBinnings()   # Store from initially-set checkboxes
        self.setDarkBinnings()

        # Set up button responders
        self.ui.saveButton.clicked.connect(self.saveButtonClicked)
        self.ui.cancelButton.clicked.connect(self.cancelButtonClicked)

        # Checkboxes for binning settings
        self.ui.biasBin11.clicked.connect(self.biasBinningsChanged)
        self.ui.biasBin22.clicked.connect(self.biasBinningsChanged)
        self.ui.biasBin33.clicked.connect(self.biasBinningsChanged)
        self.ui.biasBin44.clicked.connect(self.biasBinningsChanged)
        self.ui.darkBin11.clicked.connect(self.darkBinningsChanged)
        self.ui.darkBin22.clicked.connect(self.darkBinningsChanged)
        self.ui.darkBin33.clicked.connect(self.darkBinningsChanged)
        self.ui.darkBin44.clicked.connect(self.darkBinningsChanged)

        # Catch changes to the input fields
        self.ui.biasFramesCount.editingFinished.connect(self.biasFramesCountChanged)
        self.ui.darkFramesCount.editingFinished.connect(self.darkFramesCountChanged)
        self.ui.exposureLengths.textChanged.connect(self.exposureLengthsChanged)

        self.enableButtons()
        # print("BulkEntryDialog/init exits")

    # Set Bias binnings array from the checkboxes selected
    def setBiasBinnings(self):
        self._biasBinnings: [int] = []
        if self.ui.biasBin11.isChecked():
            self._biasBinnings.append(1)
        if self.ui.biasBin22.isChecked():
            self._biasBinnings.append(2)
        if self.ui.biasBin33.isChecked():
            self._biasBinnings.append(3)
        if self.ui.biasBin44.isChecked():
            self._biasBinnings.append(4)

    # Set Dark binnings array from the checkboxes selected
    def setDarkBinnings(self):
        self._darkBinnings: [int] = []
        if self.ui.darkBin11.isChecked():
            self._darkBinnings.append(1)
        if self.ui.darkBin22.isChecked():
            self._darkBinnings.append(2)
        if self.ui.darkBin33.isChecked():
            self._darkBinnings.append(3)
        if self.ui.darkBin44.isChecked():
            self._darkBinnings.append(4)

    # The Save button is only enabled when
    #   One or more bias frames with at least one binning are specified;   OR
    #   One or more dark frames with at least one binning and at least one exposure length
    def enableButtons(self):
        # print("enableButtons")
        enabled: bool = (self._numBiasFrames > 0 and len(self._biasBinnings) > 0)\
                        or (self._numDarkFrames > 0 and len(self._darkBinnings) > 0
                            and len(self._darkExposures) > 0)
        self.ui.saveButton.setEnabled(enabled)

    def darkBinningsChanged(self):
        self.setDarkBinnings()
        self.enableButtons()

    def biasBinningsChanged(self):
        self.setBiasBinnings()
        self.enableButtons()

    def biasFramesCountChanged(self):
        # print("biasFramesCountChanged")
        proposed_value: str = self.ui.biasFramesCount.text()
        self.ui.biasMessage.setText("")
        value: int = Validators.valid_int_in_range(proposed_value, 1, 32767)
        if value is not None:
            self._numBiasFrames = value
        else:
            self._numBiasFrames = 0
            if proposed_value != "":
                self.ui.biasMessage.setText("Invalid Bias frame count")
        self.enableButtons()

    def darkFramesCountChanged(self):
        # print("darkFramesCountChanged")
        proposed_value: str = self.ui.darkFramesCount.text()
        self.ui.darkMessage.setText("")
        value: int = Validators.valid_int_in_range(proposed_value, 1, 32767)
        if value is not None:
            self._numDarkFrames = value
        else:
            self._numDarkFrames = 0
            if proposed_value != "":
                self.ui.darkMessage.setText("Invalid Dark frame count")
        self.enableButtons()

    # Exposure lengths field has changed.
    # This is a free-form text field consisting of zero or more numbers separated by commas
    # or white space.  If it is in that format, save the numbers in the exposures array.  If not,
    # set the exposures array to empty and produce an error
    def exposureLengthsChanged(self):
        # print("exposureLengthsChanged")
        field_string: str = str(self.ui.exposureLengths.toPlainText()).strip()
        self._darkExposures = []
        self.ui.exposuresMessage.setText("")
        tokens_of_string: [str] = re.split(r"\s|,", field_string)
        for token in tokens_of_string:
            # print(f"  Check \"{token}\"")
            if len(token) > 0:
                value: float = Validators.valid_float_in_range(token, 0.0001, 24 * 60 * 60)
                if value is not None:
                    self._darkExposures.append(value)
                else:
                    self._darkExposures = []
                    self.ui.exposuresMessage.setText(f"Invalid value \"{token}\".")
        # print(f"Exposures now: {self._darkExposures}")
        self.enableButtons()

    def saveButtonClicked(self):
        self.setBiasBinnings()
        self.setDarkBinnings()
        self.exposureLengthsChanged()
        if self.ui.saveButton.isEnabled():
            self.ui.accept()
        # print("saveButtonClicked")

    def cancelButtonClicked(self):
        # print("cancelButtonClicked")
        self.ui.reject()
