#   The following method variables are accessible via getters.  No setters - no external setting.
#   _numBiasFrames      number of bias frames for each of the following binnings
#   _biasBinnings       array of binning values for bias frames.  empty if none
#   _numDarkFrames      number of dark frames for each binning and exposure
#   _darkBinnings       array of binning values for dark frames, empty if none
#   _darkExposures      array of exposure values (float, seconds) for dark frames
import re

from PyQt5.QtCore import QObject, QEvent, QSettings
from PyQt5.QtGui import QFont

from MultiOsUtil import MultiOsUtil
from tracelog import *

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
        self.ui = uic.loadUi(MultiOsUtil.path_for_file_in_program_directory("BulkEntry.ui"))

        # Set window font sizes according to saved preference
        settings = QSettings()
        standard_font_size = settings.value(MultiOsUtil.STANDARD_FONT_SIZE_SETTING)
        MultiOsUtil.set_font_sizes(parent=self.ui,
                                   standard_size=standard_font_size,
                                   title_prefix=MultiOsUtil.MAIN_TITLE_LABEL_PREFIX,
                                   title_increment=MultiOsUtil.MAIN_TITLE_FONT_SIZE_INCREMENT,
                                   subtitle_prefix=MultiOsUtil.SUBTITLE_LABEL_PREFIX,
                                   subtitle_increment=MultiOsUtil.SUBTITLE_FONT_SIZE_INCREMENT
                                   )

        self._numBiasFrames: int = 0
        self._numDarkFrames: int = 0
        self._darkExposures: [float] = []
        self._biasBinnings: [int] = []
        self._darkBinnings: [int] = []

        self.set_bias_binnings()  # Store from initially-set checkboxes
        self.set_dark_binnings()

        # Set up button responders
        self.ui.saveButton.clicked.connect(self.save_button_clicked)
        self.ui.cancelButton.clicked.connect(self.cancel_button_clicked)

        # Checkboxes for binning settings
        self.ui.biasBin11.clicked.connect(self.bias_binnings_changed)
        self.ui.biasBin22.clicked.connect(self.bias_binnings_changed)
        self.ui.biasBin33.clicked.connect(self.bias_binnings_changed)
        self.ui.biasBin44.clicked.connect(self.bias_binnings_changed)
        self.ui.darkBin11.clicked.connect(self.dark_binnings_changed)
        self.ui.darkBin22.clicked.connect(self.dark_binnings_changed)
        self.ui.darkBin33.clicked.connect(self.dark_binnings_changed)
        self.ui.darkBin44.clicked.connect(self.dark_binnings_changed)

        # Catch changes to the input fields
        self.ui.biasFramesCount.editingFinished.connect(self.bias_frames_count_changed)
        self.ui.darkFramesCount.editingFinished.connect(self.dark_frames_count_changed)
        self.ui.exposureLengths.textChanged.connect(self.exposure_lengths_changed)

        self.enable_buttons()

    # print("BulkEntryDialog/init exits")

    def set_up_ui(self):
        # Set size from last resize, if any
        settings = QSettings()
        if settings.contains(MultiOsUtil.LAST_BULKADD_SIZE_SETTING):
            last_size = settings.value(MultiOsUtil.LAST_BULKADD_SIZE_SETTING)
            self.ui.resize(last_size)

        self.ui.installEventFilter(self)

    # Set Bias binnings array from the checkboxes selected
    @tracelog
    def set_bias_binnings(self):
        """Create BiasBinnings array from checked checkboxes in dialog"""
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
    @tracelog
    def set_dark_binnings(self):
        """Create DarkBinnings array from checked checkboxes in dialog"""
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
    @tracelog
    def enable_buttons(self):
        """Enable or disable certain dialog controls according to context"""
        # print("enableButtons")
        enabled: bool = (self._numBiasFrames > 0 and len(self._biasBinnings) > 0) \
                        or (self._numDarkFrames > 0 and len(self._darkBinnings) > 0
                            and len(self._darkExposures) > 0)
        self.ui.saveButton.setEnabled(enabled)

    @tracelog
    def dark_binnings_changed(self):
        """Respond to signal that dark binnings have changed"""
        self.set_dark_binnings()
        self.enable_buttons()

    @tracelog
    def bias_binnings_changed(self):
        """Respond to signal that bias binnings have changed"""
        self.set_bias_binnings()
        self.enable_buttons()

    @tracelog
    def bias_frames_count_changed(self):
        """validate and store changed bias frame count field"""
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
        self.enable_buttons()

    @tracelog
    def dark_frames_count_changed(self):
        """validate and store changed dark frame count field"""
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
        self.enable_buttons()

    # Exposure lengths field has changed.
    # This is a free-form text field consisting of zero or more numbers separated by commas
    # or white space.  If it is in that format, save the numbers in the exposures array.  If not,
    # set the exposures array to empty and produce an error
    @tracelog
    def exposure_lengths_changed(self):
        """validate and store changed exposure length field"""
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
        self.enable_buttons()

    @tracelog
    def save_button_clicked(self, _):
        """Close the dialog with a success indicator"""
        self.set_bias_binnings()
        self.set_dark_binnings()
        self.exposure_lengths_changed()
        if self.ui.saveButton.isEnabled():
            self.ui.accept()
        # print("saveButtonClicked")

    @tracelog
    def cancel_button_clicked(self, _):
        """CLose the dialog with a cancellation signal"""
        # print("cancelButtonClicked")
        self.ui.reject()

    # Look at all events happening in this window.  If event is a resize, remember the
    # size in the settings

    def eventFilter(self, the_object: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Resize:
            window_size = event.size()
            settings = QSettings()
            settings.setValue(MultiOsUtil.LAST_BULKADD_SIZE_SETTING, window_size)
        return False  # Didn't handle event
