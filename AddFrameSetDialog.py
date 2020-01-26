from PyQt5 import uic
from PyQt5.QtWidgets import QDialog

from MultiOsUtil import MultiOsUtil
from tracelog import *

from BiasFrameSet import BiasFrameSet
from DarkFrameSet import DarkFrameSet
from FrameSet import FrameSet
from Validators import Validators


class AddFrameSetDialog(QDialog):
    def __init__(self):
        """Initialize class object on creation"""
        # print("AddFrameSetDialog/init entered")
        QDialog.__init__(self)
        self.ui = uic.loadUi(MultiOsUtil.path_for_file_in_program_directory("AddFrameSet.ui"))
        self._numFramesValid = False   # Set as part of field validation
        self._exposureValid = False
        self._completedValid = False
        self._frameSet: FrameSet
        # print("AddFrameSetDialog/init exits")

    @tracelog
    def getFrameSet(self) -> FrameSet:  # Will be DarkFrameSet or BiasFrameSet
        """Return the frameset created by this dialog after it is closed"""
        return self._frameSet

    @tracelog
    def setupUI(self, new_set: bool, frame_set=None):
        """Initialize UI fields in the dialog"""
        print("AddFrameSetDialog setupUI entered")

        # Remember the frame set that was used to set up this window.
        # If we're creating a new one, this will be None, and will result in
        # us creating the correct subclass on exit
        self._frameSet = frame_set
        init_reference = self._frameSet

        # Initialize the input fields and radio buttons to the stored frameset
        if self._frameSet is None:
            # Initialize fields using a Dark Frame
            init_reference = DarkFrameSet()
        # Initialize from given frame set
        self.ui.numberOfFrames.setText(str(init_reference.get_number_of_frames()))
        self.ui.completedFrames.setText(str(init_reference.get_number_complete()))

        if isinstance(init_reference, BiasFrameSet):
            self.ui.biasButton.setChecked(True)
            self.ui.exposureSeconds.setText("")
        else:
            assert(isinstance(init_reference, DarkFrameSet))
            self.ui.darkButton.setChecked(True)
            self.ui.exposureSeconds.setText(str(init_reference.get_exposure_seconds()))

        binning = init_reference.get_binning()
        if binning == 1:
            self.ui.binning11.setChecked(True)
        elif binning == 2:
            self.ui.binning22.setChecked(True)
        elif binning == 3:
            self.ui.binning33.setChecked(True)
        else:
            assert(binning == 4)
            self.ui.binning44.setChecked(True)

        # Catch changes to the input fields
        self.ui.numberOfFrames.editingFinished.connect(self.number_of_frames_changed)
        self.ui.exposureSeconds.editingFinished.connect(self.exposure_seconds_changed)
        self.ui.completedFrames.editingFinished.connect(self.completed_frames_changed)

        # Button responders
        self.ui.addButton.clicked.connect(self.add_button_clicked)
        self.ui.cancelButton.clicked.connect(self.cancel_button_clicked)

        # If we're defining a new set, we don't allow the Completed field to be seen or set
        if new_set:
            self.ui.completedFrames.setVisible(False)
            self.ui.completedLabel.setVisible(False)

        self._numFramesValid = True   # We know we started with a valid setup
        self._exposureValid = True   # We know we started with a valid setup
        self._completedValid = True
        self.enableControls()
        
        print("AddFrameSetDialog setupUI exits")

    #  Enable the Add button depending on validity of input fields
    @tracelog
    def enableControls(self):
        """Enable/disable certain UI controls based on context"""
        self.ui.addButton.setEnabled(self._numFramesValid and self._exposureValid
                                     and (self._completedValid or not (self.ui.completedFrames.isVisible())))

    # The value in the "Number of frames" field has been changed.
    # Validate it and, if valid, update the FrameSet we're creating or editing
    # If not valid, record that fact so the Add button becomes disabled

    @tracelog
    def number_of_frames_changed(self):
        """Validate and store change number of frames field"""
        proposed_value = self.ui.numberOfFrames.text()
        # print("numberOfFramesChanged: " + proposed_value)
        if Validators.valid_int_in_range(proposed_value, 1, 32767) is not None:
            # print(f"  Set number Of Frames to {int(proposed_value)}")
            self._numFramesValid = True
        else:
            self.ui.numberOfFrames.setText("INVALID")
            self._numFramesValid = False
        self.enableControls()

    # The value in the "Exposure time" field has been changed.
    # Validate it and, if valid, update the FrameSet we're creating or editing
    # If not valid, record that fact so the Add button becomes disabled

    @tracelog
    def exposure_seconds_changed(self):
        """Validate and store changed exposure seconds field"""
        proposed_value = self.ui.exposureSeconds.text()
        # print("exposureSecondsChanged: " + proposed_value)
        if self.ui.biasButton.isChecked():
            # Bias frame - exposure field can be blank or zero
            if proposed_value.strip() == "":
                self._exposureValid = True
            elif Validators.valid_float_in_range(proposed_value, 0, 0) is not None:
                self._exposureValid = True
            else:
                self.ui.exposureSeconds.setText("INVALID")
                self._exposureValid = False
        else:
            # Dark frame - exposure field must be positive number
            assert(self.ui.darkButton.isChecked())
            if Validators.valid_float_in_range(proposed_value, 0, 24 * 60 * 60) is not None:
                # print(f"  Set exposure time to {float(proposed_value)}")
                self._exposureValid = True
            else:
                self.ui.exposureSeconds.setText("INVALID")
                self._exposureValid = False
        self.enableControls()

    # The value in the "Number Completed" field has been changed.
    # Validate it and, if valid, update the FrameSet we're editing.
    # (This can happen only when editing, since we hide this field when creating a new FrameSet)
    # If not valid, record that fact so the Add button becomes disabled

    @tracelog
    def completed_frames_changed(self):
        """Validate and store changed 'completed frames' field"""
        proposed_value = self.ui.completedFrames.text()
        # print("completedFramesChanged, proposed \"" + proposed_value + "\"")
        if Validators.valid_int_in_range(proposed_value, 0, 32767) is not None:
            # print(f"  Set number of Completed Frames to {int(proposed_value)}")
            self._completedValid = True
        else:
            self.ui.completedFrames.setText("INVALID")
            self._completedValid = False
        self.enableControls()

    # User has clicked the "Add" button.  Return to our parent with the modified
    # frameset available for recovery

    @tracelog
    def add_button_clicked(self, _):
        """Respond to Add button - store data and end dialog"""
        # print("addButtonClicked")
        # In case the user has typed something into a field but not caused it to be
        # processed by hitting tab or enter, do another round of data entry & validation
        self.number_of_frames_changed()
        self.exposure_seconds_changed()
        if self.ui.completedFrames.isVisible():
            self.completed_frames_changed()
        # Now, if the data survived that validation, we can proceed to process the Add
        if self.ui.addButton.isEnabled():
            # Copy the edited fields back to the saved frameSet
            if self.ui.binning11.isChecked():
                binning = 1
            elif self.ui.binning22.isChecked():
                binning = 2
            elif self.ui.binning33.isChecked():
                binning = 3
            else:
                assert (self.ui.binning44.isChecked())
                binning = 4

            if self.ui.biasButton.isChecked():
                self._frameSet = BiasFrameSet(number_of_frames=int(self.ui.numberOfFrames.text()),
                                              binning=binning, number_complete=int(self.ui.completedFrames.text()))
            else:
                self._frameSet = DarkFrameSet(number_of_frames=int(self.ui.numberOfFrames.text()),
                                              exposure=float(self.ui.exposureSeconds.text()),
                                              binning=binning, number_complete=int(self.ui.completedFrames.text()))

            self.ui.accept()

    @tracelog
    def cancel_button_clicked(self, _):
        """Respond to Cancel button by closing dialog with signal not to proceed"""
        # print("cancelButtonClicked")
        # Restore the incoming frameset from the saved values
        self.ui.reject()
