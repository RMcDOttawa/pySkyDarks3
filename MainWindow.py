import json
from datetime import date, time
from time import strftime
from typing import List

from PyQt5.QtGui import QFont

from MultiOsUtil import MultiOsUtil
from tracelog import *
from PyQt5 import uic, QtWidgets, QtGui
from PyQt5.QtCore import QMutex, QItemSelection, QModelIndex, QItemSelectionModel, QTime, QThread, QTimer, \
    QSettings, QDate, QEvent, QObject
from PyQt5.QtWidgets import QMainWindow, QDialog, QMessageBox, QHeaderView, QFileDialog, QWidget, QLabel, QCheckBox, \
    QRadioButton, QLineEdit, QPushButton, QDateEdit, QTimeEdit, QListWidgetItem

from AddFrameSetDialog import AddFrameSetDialog
from BulkEntryDialog import BulkEntryDialog
from DataModel import DataModel
from DataModelDecoder import DataModelDecoder
from EndDate import EndDate
from EndTime import EndTime
from FrameSet import FrameSet
from FrameSetPlanTableModel import FrameSetPlanTableModel
from FrameSetSessionTableModel import FrameSetSessionTableModel
from RmNetUtils import RmNetUtils
from SessionController import SessionController
from SessionThreadWorker import SessionThreadWorker
from StartDate import StartDate
from StartTime import StartTime
from TheSkyX import TheSkyX
from Validators import Validators


class MainWindow(QMainWindow):
    UNSAVED_WINDOW_TITLE = "(Unsaved Document)"
    SAVED_FILE_EXTENSION = ".ewho2"
    RUN_SESSION_TAB_INDEX = 4
    INDENTATION_DEPTH = 3
    COOLER_POWER_UPDATE_INTERVAL = 20  # Update displayed cooler power this often

    def __init__(self):
        """Initialize MainWindow class"""
        QMainWindow.__init__(self)
        self.installEventFilter(self)
        self.ui = uic.loadUi(MultiOsUtil.path_for_file_in_program_directory("MainWindow.ui"))
        self._controls_connected = False
        self._file_path = ""
        self._is_dirty = False
        self._cooler_timer = None
        self._session_framesets: [FrameSet] = []
        self._thread_controller: SessionController = None
        self._mutex: QMutex = None

        # noinspection PyTypeChecker
        self._session_table_model: FrameSetSessionTableModel = None

        self.model = None
        self.ui.setWindowTitle(MainWindow.UNSAVED_WINDOW_TITLE)
        self.ui.coolerPowerLabel.setVisible(False)
        self.ui.coolerPowerValue.setVisible(False)
        self._plan_table_model = None

        # Always display the first tab on opening
        self.ui.mainTabView.setCurrentIndex(0)

        # If we have a saved window size in the preferences, set the size to that
        settings = QSettings()
        if settings.contains(MultiOsUtil.LAST_WINDOW_SIZE_SETTING):
            last_size = settings.value(MultiOsUtil.LAST_WINDOW_SIZE_SETTING)
            self.ui.resize(last_size)

        # Ensure there is a standard window font size established
        if not settings.contains(MultiOsUtil.STANDARD_FONT_SIZE_SETTING):
            settings.setValue(MultiOsUtil.STANDARD_FONT_SIZE_SETTING,
                              MultiOsUtil.STANDARD_FONT_SIZE)

        # Frame plan table headers and console table headers should auto-resize if font size changes
        self.ui.framesPlanTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ui.sessionTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        # Set font sizes of all fontable elements to the saved font size
        standard_font_size = settings.value(MultiOsUtil.STANDARD_FONT_SIZE_SETTING)
        MultiOsUtil.set_font_sizes(parent=self.ui,
                                   standard_size=standard_font_size,
                                   title_prefix=MultiOsUtil.MAIN_TITLE_LABEL_PREFIX,
                                   title_increment=MultiOsUtil.MAIN_TITLE_FONT_SIZE_INCREMENT,
                                   subtitle_prefix=MultiOsUtil.SUBTITLE_LABEL_PREFIX,
                                   subtitle_increment=MultiOsUtil.SUBTITLE_FONT_SIZE_INCREMENT
                                   )

        # "Log everything" checkbox is set from preferences, defaults to "off"
        if settings.contains(TRACE_LOG_SETTING):
            trace_enabled = bool(settings.value(TRACE_LOG_SETTING))
        else:
            settings.setValue(TRACE_LOG_SETTING, False)
            trace_enabled = False
        self.ui.writeTraceInfo.setChecked(trace_enabled)

    def set_is_dirty(self, dirty: bool):
        """Record whether the open document has unsaved changes"""
        self._is_dirty = dirty

    def is_dirty(self) -> bool:
        """Report whether the open document has unsaved changes"""
        return self._is_dirty

    @tracelog
    def accept_data_model(self, the_model: DataModel):
        """Take a data model, remember it, and use it to initialize fields"""
        self.model: DataModel = the_model
        self.ui.installEventFilter(self)

        # Location information
        self.ui.locName.setText(the_model.get_location_name())
        self.ui.timeZone.setText(str(the_model.get_time_zone()))
        self.ui.latitude.setText(str(the_model.get_latitude()))
        self.ui.longitude.setText(str(the_model.get_longitude()))

        # Start date
        self.ui.startDateNow.setChecked(the_model.get_start_date_type() == StartDate.NOW)
        self.ui.startDateToday.setChecked(the_model.get_start_date_type() == StartDate.TODAY)
        self.ui.startDateGiven.setChecked(the_model.get_start_date_type() == StartDate.GIVEN_DATE)

        given_start_date: str = the_model.get_given_start_date()
        converted_start_date = QDate.fromString(given_start_date, 'yyyy-M-d')
        self.ui.startDateEdit.setDate(converted_start_date)

        # Start time
        self.ui.startTimeSunset.setChecked(the_model.get_start_time_type() == StartTime.SUNSET)
        self.ui.startTimeCivil.setChecked(the_model.get_start_time_type() == StartTime.CIVIL_DUSK)
        self.ui.startTimeNautical.setChecked(the_model.get_start_time_type() == StartTime.NAUTICAL_DUSK)
        self.ui.startTimeAstronomical.setChecked(the_model.get_start_time_type() == StartTime.ASTRONOMICAL_DUSK)
        self.ui.startTimeGiven.setChecked(the_model.get_start_time_type() == StartTime.GIVEN_TIME)
        self.ui.startTimeEdit.setTime(QTime.fromString(the_model.get_given_start_time()))

        # End date
        self.ui.endDateWhenDone.setChecked(the_model.get_end_date_type() == EndDate.WHEN_DONE)
        self.ui.endDateTodayTomorrow.setChecked(the_model.get_end_date_type() == EndDate.TODAY_TOMORROW)
        self.ui.endDateGiven.setChecked(the_model.get_end_date_type() == EndDate.GIVEN_DATE)
        given_end_date: str = the_model.get_given_end_date()
        converted_end_date = QDate.fromString(given_end_date, 'yyyy-M-d')
        self.ui.endDateEdit.setDate(converted_end_date)

        # End time
        self.ui.endTimeSunrise.setChecked(the_model.get_end_time_type() == EndTime.SUNRISE)
        self.ui.endTimeCivil.setChecked(the_model.get_end_time_type() == EndTime.CIVIL_DAWN)
        self.ui.endTimeNautical.setChecked(the_model.get_end_time_type() == EndTime.NAUTICAL_DAWN)
        self.ui.endTimeAstronomical.setChecked(the_model.get_end_time_type() == EndTime.ASTRONOMICAL_DAWN)
        self.ui.endTimeGiven.setChecked(the_model.get_end_time_type() == EndTime.GIVEN_TIME)
        self.ui.endTimeEdit.setTime(QTime.fromString(the_model.get_given_end_time()))

        # End Processing
        self.ui.warmCCDWhenDone.setChecked(the_model.get_warm_up_when_done())
        self.ui.warmCCDSeconds.setText(str(the_model.get_warm_up_when_done_secs()))
        self.ui.disconnectWhenDone.setChecked(the_model.get_disconnect_when_done())

        # Server network address
        self.ui.serverAddress.setText(the_model.get_net_address())
        self.ui.serverPort.setText(str(the_model.get_port_number()))

        # Wake on LAN
        self.ui.sendWOLBeforeStarting.setChecked(the_model.get_send_wake_on_lan_before_starting())
        self.ui.sendWOLSecondsBefore.setText(str(the_model.get_send_wol_seconds_before()))
        self.ui.wolMacAddress.setText(the_model.getWolMacAddress())
        self.ui.wolBroadcastAddress.setText(the_model.getWolBroadcastAddress())

        # Camera Temperature controls
        self.ui.ccdIsRegulated.setChecked(the_model.get_temperature_regulated())
        self.ui.abortIfTempRises.setChecked(the_model.get_temperature_abort_on_rise())
        self.ui.targetTemperature.setText(str(the_model.get_temperature_target()))
        self.ui.temperatureTolerance.setText(str(the_model.get_temperature_within()))
        self.ui.coolingCheckInterval.setText(str(the_model.get_temperature_settle_seconds()))
        self.ui.coolingMaxTryTime.setText(str(the_model.get_max_cooling_wait_time()))
        self.ui.coolingMaxRetryCount.setText(str(the_model.get_temperature_fail_retry_count()))
        self.ui.coolingRetryDelay.setText(str(the_model.get_temperature_fail_retry_delay_seconds()))
        self.ui.tempRiseAbortThreshold.setText(str(the_model.get_temperature_abort_rise_limit()))

        # Framesets
        self._plan_table_model = FrameSetPlanTableModel(the_model)
        self.ui.framesPlanTable.setModel(self._plan_table_model)

        # Autosave
        self.ui.autoSaveAfterEach.setChecked(the_model.get_auto_save_after_each_frame())

        # Autosave path from camera - no initialization, set up when connected to camera
        # Console log list view needs no initialization - it's set up when session is started
        # Images being acquired (subset of plan) needs no initialization - set up on tab pane entry

        self.connect_controls()
        self.set_is_dirty(False)
        self.calculate_sun_based_times()
        self.enable_controls()

    @tracelog
    def connect_controls(self):
        """Connect responder methods to all the controls in the window"""
        # Catching changes to the table selection must be set up each time
        # (Determined this experimentally - not intuitive, but what the hell)
        table_selection_model = self.ui.framesPlanTable.selectionModel()
        table_selection_model.selectionChanged.connect(self.frames_plan_table_selection_changed)

        # But the majority of responders should be set up only once.
        if self._controls_connected:
            # print("Controls already connected")
            pass
        else:
            # print("Connecting controls to responders")
            self._controls_connected = True
            self.ui.testConnectionButton.clicked.connect(self.test_connection_button_clicked)
            self.ui.sendWolNowButton.clicked.connect(self.send_wol_now_button_clicked)
            self.ui.locName.editingFinished.connect(self.loc_name_edit_finished)

            # start date buttons
            self.ui.startDateNow.clicked.connect(self.start_date_now_clicked)
            self.ui.startDateToday.clicked.connect(self.start_date_today_clicked)
            self.ui.startDateGiven.clicked.connect(self.start_date_given_clicked)

            # start time buttons
            self.ui.startTimeSunset.clicked.connect(self.start_time_sunset_clicked)
            self.ui.startTimeCivil.clicked.connect(self.start_time_civil_clicked)
            self.ui.startTimeNautical.clicked.connect(self.start_time_nautical_clicked)
            self.ui.startTimeAstronomical.clicked.connect(self.start_time_astronomical_clicked)
            self.ui.startTimeGiven.clicked.connect(self.start_time_given_clicked)

            # start date picker
            self.ui.startDateEdit.dateChanged.connect(self.start_date_edit_changed)

            # start time picker
            self.ui.startTimeEdit.timeChanged.connect(self.start_time_edit_changed)

            # end date buttons
            self.ui.endDateWhenDone.clicked.connect(self.end_date_when_done_clicked)
            self.ui.endDateTodayTomorrow.clicked.connect(self.end_date_today_tomorrow_clicked)
            self.ui.endDateGiven.clicked.connect(self.end_date_given_clicked)

            # end time buttons
            self.ui.endTimeSunrise.clicked.connect(self.end_time_sunrise_clicked)
            self.ui.endTimeCivil.clicked.connect(self.end_time_civil_clicked)
            self.ui.endTimeNautical.clicked.connect(self.end_time_nautical_clicked)
            self.ui.endTimeAstronomical.clicked.connect(self.end_time_astronomical_clicked)
            self.ui.endTimeGiven.clicked.connect(self.end_time_given_clicked)

            # end date picker
            self.ui.endDateEdit.dateChanged.connect(self.end_date_edit_changed)

            # end time picker
            self.ui.endTimeEdit.timeChanged.connect(self.end_time_edit_changed)

            # Catch input: timezone
            self.ui.timeZone.editingFinished.connect(self.time_zone_edit_finished)

            # Catch input: latitude
            self.ui.latitude.editingFinished.connect(self.latitude_edit_finished)

            # Catch input: longitude
            self.ui.longitude.editingFinished.connect(self.longitude_edit_finished)

            # Catch input: Warm CCD checkbox
            self.ui.warmCCDWhenDone.clicked.connect(self.warm_ccd_when_done_clicked)

            # Catch input: CCD warm-up time
            self.ui.warmCCDSeconds.editingFinished.connect(self.warm_ccd_seconds_finished)

            # Catch input: disconnect camera checkbox
            self.ui.disconnectWhenDone.clicked.connect(self.disconnect_when_done_clicked)

            # Catch input: temp regulated checkbox
            self.ui.ccdIsRegulated.clicked.connect(self.ccd_is_regulated_clicked)

            # Catch input: target temperature
            self.ui.targetTemperature.editingFinished.connect(self.target_temperature_finished)

            # Catch input: temperature within tolerance
            self.ui.temperatureTolerance.editingFinished.connect(self.temperature_tolerance_finished)

            # Catch input: cooling check interval
            self.ui.coolingCheckInterval.editingFinished.connect(self.cooling_check_interval_finished)

            # Catch input: max time to try to cool to target
            self.ui.coolingMaxTryTime.editingFinished.connect(self.cooling_max_try_time_finished)

            # Catch input: cooling retry count
            self.ui.coolingMaxRetryCount.editingFinished.connect(self.cooling_max_retry_count_finished)

            # Catch input: cooling retry delay
            self.ui.coolingRetryDelay.editingFinished.connect(self.cooling_retry_delay_finished)

            # Catch input: temp rise abort amount
            self.ui.tempRiseAbortThreshold.editingFinished.connect(self.temp_rise_abort_threshold_finished)

            # Catch input: temp rise abort checkbox
            self.ui.abortIfTempRises.clicked.connect(self.abort_if_temp_rises_clicked)

            # Catch input: server address
            self.ui.serverAddress.editingFinished.connect(self.server_address_finished)

            # Catch input: server port number
            self.ui.serverPort.editingFinished.connect(self.server_port_finished)

            # Catch input: WOL checkbox
            self.ui.sendWOLBeforeStarting.clicked.connect(self.send_wol_before_starting_clicked)

            # Catch input: WOL delay
            self.ui.sendWOLSecondsBefore.editingFinished.connect(self.send_wol_seconds_before_finished)

            # Catch input: WOL MAC address
            self.ui.wolMacAddress.editingFinished.connect(self.wol_mac_address_finished)

            # WOL broadcast address
            self.ui.wolBroadcastAddress.editingFinished.connect(self.wol_broadcast_address_finished)

            # Buttons for manipulating Frames Plan
            self.ui.addFrameButton.clicked.connect(self.add_frame_button_clicked)
            self.ui.deleteFrameButton.clicked.connect(self.delete_frame_button_clicked)
            self.ui.editFrameButton.clicked.connect(self.edit_frame_button_clicked)
            self.ui.framesPlanTable.doubleClicked.connect(self.frame_table_double_clicked)
            self.ui.bulkAddButton.clicked.connect(self.bulk_add_button_clicked)
            self.ui.frameUpButton.clicked.connect(self.frame_up_button_clicked)
            self.ui.frameDownButton.clicked.connect(self.frame_down_button_clicked)
            self.ui.resetCompleted.clicked.connect(self.reset_completed_counts)

            # autosave checkbox
            self.ui.autoSaveAfterEach.clicked.connect(self.auto_save_after_each_clicked)

            # Session begin and cancel buttons
            self.ui.beginSessionButton.clicked.connect(self.begin_session_button_clicked)
            self.ui.cancelSessionButton.clicked.connect(self.cancel_session_button_clicked)

            # Menu items
            self.ui.menuSaveAs.triggered.connect(self.save_as_menu_triggered)
            self.ui.menuSave.triggered.connect(self.save_menu_triggered)
            self.ui.menuClose.triggered.connect(self.close_menu_triggered)
            self.ui.menuNew.triggered.connect(self.new_menu_triggered)
            self.ui.menuOpen.triggered.connect(self.open_menu_triggered)
            self.ui.actionFontLarger.triggered.connect(self.font_size_larger)
            self.ui.actionFontSmaller.triggered.connect(self.font_size_smaller)
            self.ui.actionFontReset.triggered.connect(self.font_size_reset)

            # Checkbox for tracing
            self.ui.writeTraceInfo.clicked.connect(self.write_trace_info_clicked)

            # Tab view
            # See when tabs are changed so we can do special init as needed
            # (at presently only applies to "run session" tab.  There is no way to
            # connect to individual tabs, we must catch the signal from the tabView and
            # then check the index for which tab was selected
            self.ui.mainTabView.currentChanged.connect(self.tab_view_tab_changed)

            # Catch "about to quit" from Application so we can protect against the Quit menu
            app = QtWidgets.QApplication.instance()
            assert (app is not None)
            app.aboutToQuit.connect(self.app_about_to_quit)

    @tracelog
    def enable_controls(self):
        """Set enabled-disabled status of some controls depending on data settings"""
        # print("enableControls")

        # Enable sunrise-based times only when latitude & longitude are known
        sunrise_capable: bool = self.model.can_calculate_sunrise()
        start_not_now = not (self.model.get_start_date_type() == StartDate.NOW)
        end_not_when_done = not (self.model.get_end_date_type() == EndDate.WHEN_DONE)

        self.ui.startTimeSunset.setEnabled(sunrise_capable and start_not_now)
        self.ui.startTimeCivil.setEnabled(sunrise_capable and start_not_now)
        self.ui.startTimeNautical.setEnabled(sunrise_capable and start_not_now)
        self.ui.startTimeAstronomical.setEnabled(sunrise_capable and start_not_now)
        self.ui.startTimeGiven.setEnabled(sunrise_capable and start_not_now)

        self.ui.endTimeSunrise.setEnabled(sunrise_capable and end_not_when_done)
        self.ui.endTimeCivil.setEnabled(sunrise_capable and end_not_when_done)
        self.ui.endTimeNautical.setEnabled(sunrise_capable and end_not_when_done)
        self.ui.endTimeAstronomical.setEnabled(sunrise_capable and end_not_when_done)
        self.ui.endTimeGiven.setEnabled(sunrise_capable and end_not_when_done)

        # Start date enabled when given selected
        self.ui.startDateEdit.setEnabled(self.model.get_start_date_type() == StartDate.GIVEN_DATE and start_not_now)

        # start time enabled when given selected
        self.ui.startTimeEdit.setEnabled(self.model.get_start_time_type() == StartTime.GIVEN_TIME and start_not_now)

        # End date enabled when given selected
        self.ui.endDateEdit.setEnabled(self.model.get_end_date_type() == EndDate.GIVEN_DATE and end_not_when_done)

        # End time enabled when given selected
        self.ui.endTimeEdit.setEnabled(self.model.get_end_time_type() == EndTime.GIVEN_TIME and end_not_when_done)

        # CCD warm-up seconds when warm-up selected
        self.ui.warmCCDSeconds.setEnabled(self.model.get_warm_up_when_done())

        # 6 fields enabled when CCD Regulated is selected
        is_regulated = self.model.get_temperature_regulated()
        self.ui.targetTemperature.setEnabled(is_regulated)
        self.ui.temperatureTolerance.setEnabled(is_regulated)
        self.ui.coolingCheckInterval.setEnabled(is_regulated)
        self.ui.coolingMaxTryTime.setEnabled(is_regulated)
        self.ui.coolingMaxRetryCount.setEnabled(is_regulated)
        self.ui.coolingRetryDelay.setEnabled(is_regulated)

        # Temp rise threshold enabled when Regulated and AbortIfRise selected
        self.ui.abortIfTempRises.setEnabled(is_regulated)
        self.ui.tempRiseAbortThreshold.setEnabled(is_regulated and self.model.get_temperature_abort_on_rise())

        # 3 WOL fields if WOL selected
        wol_selected = self.model.get_send_wake_on_lan_before_starting()
        self.ui.sendWOLSecondsBefore.setEnabled(wol_selected)
        self.ui.wolMacAddress.setEnabled(wol_selected)
        self.ui.wolBroadcastAddress.setEnabled(wol_selected)

        # SendWOL if MAc and Broadcast are given
        mac_addr_given = self.model.getWolMacAddress().strip() != ""
        wol_broadcast_given = self.model.getWolBroadcastAddress().strip() != ""
        self.ui.sendWolNowButton.setEnabled(mac_addr_given and wol_broadcast_given)

        # TestConnection if server and port given
        server_addr_given = self.model.get_net_address().strip() != ""
        server_port_given = self.model.get_port_number().strip() != ""
        self.ui.testConnectionButton.setEnabled(server_addr_given and server_port_given)

        # "+" and "Bulk Add" buttons enabled if zero or one lines are selected
        # (Zero so we add to end, 1 to insert before it)
        frame_plan_selected_rows = self.frame_plan_selected_rows()
        num_selected = len(frame_plan_selected_rows)
        self.ui.addFrameButton.setEnabled((num_selected == 0) or (num_selected == 1))
        self.ui.bulkAddButton.setEnabled((num_selected == 0) or (num_selected == 1))

        # Enable "reset completed" only when there are completed frames we could reset
        self.ui.resetCompleted.setEnabled(self.model.any_nonzero_completed_counts())

        # "-" button enabled if one or more lines selected
        self.ui.deleteFrameButton.setEnabled(num_selected > 0)

        # Edit if exactly one line selected
        self.ui.editFrameButton.setEnabled(len(frame_plan_selected_rows) == 1)

        # Up If >= 1 line selected not including first one
        any_selected = len(frame_plan_selected_rows) > 0
        first_selected = 0 in frame_plan_selected_rows
        # print(f"Selected rows: {frame_plan_selected_rows} first={first_selected}")
        self.ui.frameUpButton.setEnabled(any_selected and (not first_selected))

        # Down if >= 1 line selected not including last one
        last_selected = (len(self.model.get_saved_frame_sets()) - 1) in frame_plan_selected_rows
        self.ui.frameDownButton.setEnabled(any_selected and (not last_selected))

        # Run Session tab if session is ready (server and at least one frame)
        self.ui.mainTabView.setTabEnabled(self.RUN_SESSION_TAB_INDEX, self.model.session_ready_to_run())

    @tracelog
    def test_connection_button_clicked(self, _):
        """Try to connect to the server and report if successful"""
        # print("testConnectionButtonClicked")
        # Lock-in any changes to network fields (in case user is focused on one
        # and hasn't hit enter before clicking the test connection button)
        self.server_address_finished()
        self.server_port_finished()
        if self.ui.testConnectionButton.isEnabled():
            success, message = RmNetUtils.test_connection(self.model.get_net_address(), self.model.get_port_number())
            if success:
                self.ui.testConnectionMessage.setText("Connection Successful")
            else:
                self.ui.testConnectionMessage.setText(message)

    @tracelog
    def send_wol_now_button_clicked(self, _):
        """Broadcast wake-on-lan packet over network"""
        # print("sendWolNowButtonClicked")
        # Lock-in any changes to WOL fields (in case user is focused on one
        # and hasn't hit enter before clicking the test connection button)
        self.wol_mac_address_finished()
        self.wol_broadcast_address_finished()
        if self.ui.sendWolNowButton.isEnabled():
            # Still good to go after locking-in data fields.  Try the WOL
            success, message = RmNetUtils.send_wake_on_lan(self.model.getWolBroadcastAddress(),
                                                           self.model.getWolMacAddress())
            if success:
                self.ui.testWOLMessage.setText("Sent Successfully")
            else:
                self.ui.testWOLMessage.setText(message)

    @tracelog
    def frames_plan_table_selection_changed(self, _1, _2):
        """Respond to user selecting a row in the frames plan table"""
        # print("framesPlanTableSelectionChanged")
        self.enable_controls()

    # Input field catchers

    @tracelog
    def loc_name_edit_finished(self):
        """Handle user editing the location name"""
        # print("locNameEditFinished")
        self.model.set_location_name(self.ui.locName.text())
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def time_zone_edit_finished(self):
        """Handle user editing the time zone: validate and store it"""
        # print("timeZoneEditFinished")
        proposed_value: str = self.ui.timeZone.text()
        converted_value: float = Validators.valid_int_in_range(proposed_value, -24, +24)
        if converted_value is not None:
            if converted_value != self.model.get_time_zone():
                self.set_is_dirty(True)
            self.model.set_time_zone(converted_value)
        else:
            self.model.set_time_zone(DataModel.TIMEZONE_NULL)
            self.ui.timeZone.setText("INVALID")
        self.enable_controls()

    @tracelog
    def latitude_edit_finished(self):
        """Validate and store entered Latitude value"""
        # print("latitudeEditFinished")
        proposed_value: str = self.ui.latitude.text()
        converted_value: float = Validators.valid_float_in_range(proposed_value, -90.0, +90.0)
        if converted_value is not None:
            self.model.set_latitude(converted_value)
            self.set_is_dirty(True)
        else:
            self.model.set_latitude(DataModel.LATITUDE_NULL)
            self.ui.latitude.setText("INVALID")
        self.enable_controls()

    @tracelog
    def longitude_edit_finished(self):
        """Validate and store entered Longitude value"""
        # print("longitudeEditFinished")
        proposed_value: str = self.ui.longitude.text()
        converted_value: float = Validators.valid_float_in_range(proposed_value, -180.0, +180.0)
        if converted_value is not None:
            self.model.set_longitude(converted_value)
            self.set_is_dirty(True)
        else:
            self.model.set_longitude(DataModel.LONGITUDE_NULL)
            self.ui.longitude.setText("INVALID")
        self.enable_controls()

    @tracelog
    def start_date_now_clicked(self, _):
        """Record user request that session should start NOW"""
        # print("startDateNowClicked")
        self.model.set_start_date_type(StartDate.NOW)
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def start_date_today_clicked(self, _):
        """Record user request that session should start today at a given time"""
        # print("startDateTodayClicked")
        self.model.set_start_date_type(StartDate.TODAY)
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def start_date_given_clicked(self, _):
        """Record user request that session should start on a given date at a given time"""
        # print("startDateGivenClicked")
        self.model.set_start_date_type(StartDate.GIVEN_DATE)
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def start_time_sunset_clicked(self, _):
        """Record user request that session should start at sunset"""
        # print("startTimeSunsetClicked")
        self.model.set_start_time_type(StartTime.SUNSET)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def start_time_civil_clicked(self, _):
        """Record user request that session should start at civil dusk"""
        # print("startTimeCivilClicked")
        self.model.set_start_time_type(StartTime.CIVIL_DUSK)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def start_time_nautical_clicked(self, _):
        """Record user request that session should start at nautical dusk"""
        # print("startTimeNauticalClicked")
        self.model.set_start_time_type(StartTime.NAUTICAL_DUSK)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def start_time_astronomical_clicked(self, _):
        """Record user request that session should start at astronomical dusk"""
        # print("startTimeAstronomicalClicked")
        self.model.set_start_time_type(StartTime.ASTRONOMICAL_DUSK)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def start_time_given_clicked(self, _):
        """Record user request that session should start at a specified time"""
        # print("startTimeGivenClicked")
        self.model.set_start_time_type(StartTime.GIVEN_TIME)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def end_date_when_done_clicked(self, _):
        """Record user request that session should keep going until all frames done"""
        # print("endDateWhenDoneClicked")
        self.model.set_end_date_type(EndDate.WHEN_DONE)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def end_date_today_tomorrow_clicked(self, _):
        """Record user request that session should end today or tomorrow at given time"""
        # print("endDateTodayTomorrowClicked")
        self.model.set_end_date_type(EndDate.TODAY_TOMORROW)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def end_date_given_clicked(self, _):
        """Record user request that session should end on given date"""
        # print("endDateGivenClicked")
        self.model.set_end_date_type(EndDate.GIVEN_DATE)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def end_time_sunrise_clicked(self, _):
        """Record user request that session should end at sunrise"""
        # print("endTimeSunriseClicked")
        self.model.set_end_time_type(EndTime.SUNRISE)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def end_time_civil_clicked(self, _):
        """Record user request that session should end at civil dawn"""
        # print("endTimeCivilClicked")
        self.model.set_end_time_type(EndTime.CIVIL_DAWN)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def end_time_nautical_clicked(self, _):
        """Record user request that session should end at nautical dawn"""
        # print("endTimeNauticalClicked")
        self.model.set_end_time_type(EndTime.NAUTICAL_DAWN)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def end_time_astronomical_clicked(self, _):
        """Record user request that session should end at astronomical dawn"""
        # print("endTimeAstronomicalClicked")
        self.model.set_end_time_type(EndTime.ASTRONOMICAL_DAWN)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def end_time_given_clicked(self, _):
        """Record user request that session should end at the given time"""
        # print("endTimeGivenClicked")
        self.model.set_end_time_type(EndTime.GIVEN_TIME)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def start_date_edit_changed(self, _):
        """User has edited the start date picker, store date"""
        # print("startDateEditChanged")
        new_start_date = self.ui.startDateEdit.date()
        date_as_string = new_start_date.toString("yyyy-MM-dd")
        self.model.set_given_start_date(date_as_string)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def start_time_edit_changed(self, _):
        """User has edited the start time picker, store time"""
        # print("startTimeEditChanged")
        new_start_time = self.ui.startTimeEdit.time()
        time_as_string = new_start_time.toString("HH:mm")
        self.model.set_given_start_time(time_as_string)
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def end_date_edit_changed(self, _):
        """User has edited the end date picker, store date"""
        # print("endDateEditChanged")
        new_end_date = self.ui.endDateEdit.date()
        date_as_string = new_end_date.toString("yyyy-MM-dd")
        self.model.set_given_end_date(date_as_string)
        self.calculate_sun_based_times()
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def end_time_edit_changed(self, _):
        """User has edited the end time picker, store time"""
        # print("endTimeEditChanged")
        new_end_time = self.ui.endTimeEdit.time()
        time_as_string = new_end_time.toString("HH:mm")
        self.model.set_given_end_time(time_as_string)
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def disconnect_when_done_clicked(self, _):
        """User has toggled the 'disconnect when done' box - record setting"""
        # print("disconnectWhenDoneClicked")
        self.model.set_warm_up_when_done(self.ui.disconnectWhenDone.isChecked())
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def auto_save_after_each_clicked(self, _):
        """User has toggled the 'autosave after each frame' box - record setting"""
        # print("autoSaveAfterEachClicked")
        self.model.set_auto_save_after_each_frame(self.ui.autoSaveAfterEach.isChecked())
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def warm_ccd_seconds_finished(self):
        """Validate and store a new value in the 'warm up CCD seconds' field"""
        # print("warmCCDSecondsFinished")
        proposed_value: str = self.ui.warmCCDSeconds.text()
        converted_value: int = Validators.valid_int_in_range(proposed_value, 0, 24 * 60 * 60)
        if converted_value is not None:
            self.model.set_warm_up_when_done_secs(converted_value)
            self.set_is_dirty(True)
        else:
            self.ui.warmCCDSeconds.setText("INVALID")
        self.enable_controls()

    @tracelog
    def warm_ccd_when_done_clicked(self, _):
        """User has toggled the 'warm ccd when done' box - record setting"""
        # print("warmCCDWhenDoneClicked")
        self.model.set_warm_up_when_done(self.ui.warmCCDWhenDone.isChecked())
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def ccd_is_regulated_clicked(self, _):
        """User has toggled the 'use temperature regulation' box - record setting"""
        # print("ccdIsRegulatedClicked")
        self.model.set_temperature_regulated(self.ui.ccdIsRegulated.isChecked())
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def abort_if_temp_rises_clicked(self, _):
        """User has toggled the 'abort if temperature rises' box - record setting"""
        # print("abortIfTempRisesClicked")
        self.model.set_temperature_abort_on_rise(self.ui.abortIfTempRises.isChecked())
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def send_wol_before_starting_clicked(self, _):
        """User has toggled the 'send wake on lan before starting' box - record setting"""
        # print("sendWOLBeforeStartingClicked")
        self.model.set_send_wake_on_lan_before_starting(self.ui.sendWOLBeforeStarting.isChecked())
        self.set_is_dirty(True)
        self.enable_controls()

    @tracelog
    def target_temperature_finished(self):
        """Validate and record new value entered in target temperature field"""
        # print("targetTemperatureFinished")
        proposed_value: str = self.ui.targetTemperature.text()
        converted_value: float = Validators.valid_float_in_range(proposed_value, -273.0, +100.0)
        if converted_value is not None:
            self.model.set_temperature_target(converted_value)
            self.set_is_dirty(True)
        else:
            self.ui.targetTemperature.setText("INVALID")
        self.enable_controls()

    @tracelog
    def temperature_tolerance_finished(self):
        """Validate and record new value entered in target temperature tolerance field"""
        # print("temperatureToleranceFinished")
        proposed_value: str = self.ui.temperatureTolerance.text()
        converted_value: float = Validators.valid_float_in_range(proposed_value, -50.0, +50.0)
        if converted_value is not None:
            self.model.set_temperature_within(converted_value)
            self.set_is_dirty(True)
        else:
            self.ui.temperatureTolerance.setText("INVALID")
        self.enable_controls()

    @tracelog
    def cooling_check_interval_finished(self):
        """Validate and record new value entered in cooling check interval field"""
        # print("coolingCheckIntervalFinished")
        proposed_value: str = self.ui.coolingCheckInterval.text()
        converted_value: float = Validators.valid_float_in_range(proposed_value, 0.0, 10 * 60)
        if converted_value is not None:
            self.model.set_temperature_settle_seconds(converted_value)
            self.set_is_dirty(True)
        else:
            self.ui.coolingCheckInterval.setText("INVALID")
        self.enable_controls()

    @tracelog
    def cooling_max_try_time_finished(self):
        """Validate and record new value entered in max cooling time field"""
        # print("coolingMaxTryTimeFinished")
        proposed_value: str = self.ui.coolingMaxTryTime.text()
        converted_value: float = Validators.valid_float_in_range(proposed_value, 0.0, 12 * 60 * 60)
        if converted_value is not None:
            self.model.set_max_cooling_wait_time(converted_value)
            self.set_is_dirty(True)
        else:
            self.ui.coolingMaxTryTime.setText("INVALID")
        self.enable_controls()

    @tracelog
    def cooling_max_retry_count_finished(self):
        """Validate and record new value entered in cooling retry count field"""
        # print("coolingMaxRetryCountFinished")
        proposed_value: str = self.ui.coolingMaxRetryCount.text()
        converted_value: int = Validators.valid_int_in_range(proposed_value, 0, 100)
        if converted_value is not None:
            self.model.set_temperature_fail_retry_count(converted_value)
            self.set_is_dirty(True)
        else:
            self.ui.coolingMaxRetryCount.setText("INVALID")
        self.enable_controls()

    @tracelog
    def cooling_retry_delay_finished(self):
        """Validate and record new value entered in 'delay between cooling retries' field"""
        # print("coolingRetryDelayFinished")
        proposed_value: str = self.ui.coolingRetryDelay.text()
        converted_value: float = Validators.valid_float_in_range(proposed_value, 0, 12 * 60 * 60)
        if converted_value is not None:
            self.model.set_temperature_fail_retry_delay_seconds(converted_value)
            self.set_is_dirty(True)
        else:
            self.ui.coolingRetryDelay.setText("INVALID")
        self.enable_controls()

    @tracelog
    def temp_rise_abort_threshold_finished(self):
        """Validate and record new value entered in temperature abort threshold field"""
        # print("tempRiseAbortThresholdFinished")
        proposed_value: str = self.ui.tempRiseAbortThreshold.text()
        converted_value: float = Validators.valid_float_in_range(proposed_value, 0.001, 100)
        if converted_value is not None:
            self.model.set_temperature_abort_rise_limit(converted_value)
            self.set_is_dirty(True)
        else:
            self.ui.tempRiseAbortThreshold.setText("INVALID")
        self.enable_controls()

    @tracelog
    def server_address_finished(self):
        """Validate and record new value entered in server address field"""
        # print("serverAddressFinished")
        proposed_value: str = self.ui.serverAddress.text()
        if RmNetUtils.valid_server_address(proposed_value):
            self.model.set_net_address(proposed_value)
            self.set_is_dirty(True)
        else:
            self.ui.serverAddress.setText("INVALID")
        self.enable_controls()

    @tracelog
    def wol_mac_address_finished(self):
        """Validate and record new value entered in MAC address field"""
        # print("wolMacAddressFinished")
        proposed_value: str = self.ui.wolMacAddress.text()
        if RmNetUtils.valid_mac_address(proposed_value):
            self.model.setWolMacAddress(proposed_value)
            self.set_is_dirty(True)
        else:
            self.ui.wolMacAddress.setText("INVALID")
        self.enable_controls()

    @tracelog
    def server_port_finished(self):
        """Validate and record new value entered in server port number field"""
        # print("serverPortFinished")
        proposed_value: str = self.ui.serverPort.text()
        converted_value: int = Validators.valid_int_in_range(proposed_value, 0, 65535)
        if converted_value is not None:
            self.model.set_port_number(proposed_value)
            self.set_is_dirty(True)
        else:
            self.ui.serverPort.setText("INVALID")
        self.enable_controls()

    @tracelog
    def send_wol_seconds_before_finished(self):
        """Validate and record new value entered in WOL lead time field"""
        # print("sendWOLSecondsBeforeFinished")
        proposed_value: str = self.ui.sendWOLSecondsBefore.text()
        converted_value: float = Validators.valid_float_in_range(proposed_value, 0., 24 * 60 * 60)
        if converted_value is not None:
            self.model.set_send_wol_seconds_before(converted_value)
            self.set_is_dirty(True)
        else:
            self.ui.sendWOLSecondsBefore.setText("INVALID")
        self.enable_controls()

    @tracelog
    def wol_broadcast_address_finished(self):
        """Validate and record new value entered in WOL broadcast IP address field"""
        # print("wolBroadcastAddressFinished")
        proposed_value: str = self.ui.wolBroadcastAddress.text()
        if RmNetUtils.valid_ip_address(proposed_value):
            self.model.setWolBroadcastAddress(proposed_value)
            self.set_is_dirty(True)
        else:
            self.ui.wolBroadcastAddress.setText("INVALID")
        self.enable_controls()

    # Buttons for manipulating the Frames plan

    # The "add frameset" button has been clicked.  Open a dialog form where
    # the user can specify the details of the frameset.  Modal wait for the
    # form to be submitted, and deal with the results if not cancelled.
    @tracelog
    def add_frame_button_clicked(self, _):
        """Respond to 'add frame' button by opening new frame dialog"""
        # print("addFrameButtonClicked entered")
        dialog: AddFrameSetDialog = AddFrameSetDialog()
        dialog.setupUI(new_set=True)
        result: QDialog.DialogCode = dialog.ui.exec_()
        # print(f"  Dialog returned with {result}")
        if result == QDialog.Accepted:
            self.set_is_dirty(True)
            # print(f"   Process new FrameSet: {str(dialog.getFrameSet())}")
            rows_selected = self.frame_plan_selected_rows()
            if len(rows_selected) == 0:
                # print("       Nothing selected, add to end.")
                self._plan_table_model.addFrameSet(dialog.getFrameSet())
                last_row = len(self.model.get_saved_frame_sets()) - 1
                self.frame_plan_select_rows([last_row])  # select just-added row
            else:
                assert (len(rows_selected) == 1)
                # print(f"       Insert before row {rows_selected[0]}")
                self._plan_table_model.insertFrameSet(dialog.getFrameSet(), rows_selected[0])
                self.frame_plan_select_rows([rows_selected[0]])  # select just-added row
        self.enable_controls()
        # print("addFrameButtonClicked exits")

    # One row is selected and the user has clicked "Edit"
    # We use the same dialog as adding a new frame, but pre-populate it with the selected frame
    @tracelog
    def edit_frame_button_clicked(self, _):
        """Respond to 'edit frame' button by opening edit frame dialog"""
        # print("editFrameButtonClicked Entered")

        # Get the frameset that we'll edit
        rows_selected: [int] = self.frame_plan_selected_rows()
        assert (len(rows_selected) == 1)
        frame_editing: FrameSet = self.model.get_frame_set(rows_selected[0])
        # print(f"  Editing: {frame_editing}")

        # Open the add/edit dialog with this frame set filled in t the fields
        dialog: AddFrameSetDialog = AddFrameSetDialog()
        dialog.setupUI(new_set=False, frame_set=frame_editing)
        result: QDialog.DialogCode = dialog.ui.exec_()
        # print(f"  Dialog returned with {result}")
        if result == QDialog.Accepted:
            # The edit dialog contains a new frame set with the edits
            # replace the one we edited with this new one
            self.model.set_frame_set(rows_selected[0], dialog.getFrameSet())
            self.set_is_dirty(True)
            # print(f"   Process edited FrameSet {rows_selected[0]}: {str(dialog.getFrameSet())}")
        self.enable_controls()

        # print("editFrameButtonClicked Exits")

    # A line in the table has been double-clicked. Try to treat like the Edit button
    # "Try" because we Edit only if exactly one row is selected
    @tracelog
    def frame_table_double_clicked(self, _):
        """treat double-click in the frame table the same as clicking Edit"""
        # print("frameTableDoubleClicked")
        rows_selected: [int] = self.frame_plan_selected_rows()
        if len(rows_selected) == 1:
            self.edit_frame_button_clicked(None)

    # One or more rows are selected, and we want to delete them.
    # We'll sort the row indexes and delete from max to min so the indexes don't
    # change once we start deleting.
    @tracelog
    def delete_frame_button_clicked(self, _):
        """delete the selected row in the frame plan table"""
        # print("deleteFrameButtonClicked entered")
        rows_selected: [int] = self.frame_plan_selected_rows()
        rows_selected.sort(reverse=True)
        for row_index in rows_selected:
            self._plan_table_model.deleteRow(row_index)
            self.set_is_dirty(True)
        self.enable_controls()
        # print("deleteFrameButtonClicked exits")

    # The "Bulk Add" button has been clicked.  This will be the most common way most users
    # enter their initial plan.  We open a dialog where they can specify exposure times and
    # binning values, and we'll generate every combination of those.

    @tracelog
    def bulk_add_button_clicked(self, _):
        """Respond to 'bulk add' button by opening dialog to specify multiple frames"""
        rows_selected = self.frame_plan_selected_rows()
        dialog: BulkEntryDialog = BulkEntryDialog()
        dialog.set_up_ui()
        result: QDialog.DialogCode = dialog.ui.exec_()
        if result == QDialog.Accepted:
            framesets_to_add: [FrameSet] = self.model.generate_frame_sets(dialog.getNumBiasFrames(),
                                                                          dialog.getBiasBinnings(),
                                                                          dialog.getNumDarkFrames(),
                                                                          dialog.getDarkBinnings(),
                                                                          dialog.getDarkExposures())
            insertion_point: int = None if len(rows_selected) == 0 else rows_selected[0]
            for frame_set in framesets_to_add:
                self.set_is_dirty(True)
                if insertion_point is None:
                    # print("       Nothing selected, add to end.")
                    self._plan_table_model.addFrameSet(frame_set)
                else:
                    # print(f"       Insert before row {insertion_point}")
                    self._plan_table_model.insertFrameSet(frame_set, insertion_point)
                    # Move insertion point down one because the set just got larger
                    insertion_point += 1
        dialog.close()
        self.enable_controls()

    # "Reset Completed" has been clicked.
    #  Do a "are you sure" dialog, then set all the completed counts in the plan to zero
    @tracelog
    def reset_completed_counts(self, _):
        """Set all the completed counts in the frame plan bck to zero after a confirmation dialog"""
        # print("reset_completed_counts")
        confirmation_dialog: QMessageBox = QMessageBox()
        confirmation_dialog.setWindowTitle("Confirm Reset")
        confirmation_dialog.setText("Confirm: Reset all the completed counts to zero?")
        confirmation_dialog.setInformativeText("This will cause all the plan's frame sets to be re-acquired")
        confirmation_dialog.setStandardButtons(QMessageBox.Reset | QMessageBox.Cancel)
        confirmation_dialog.setDefaultButton(QMessageBox.Reset)
        dialog_result = confirmation_dialog.exec_()
        # print(f"   Dialog returned {dialog_result}")
        if dialog_result == QMessageBox.Reset:
            # print("Reset is confirmed")
            self.model.reset_completed_counts()
            # Force a new save so the file isn't accidentally overwritten
            self._file_path = ""
            self.ui.setWindowTitle(MainWindow.UNSAVED_WINDOW_TITLE)
        self.enable_controls()
        self.set_is_dirty(True)

    # One or more lines are selected, not including the first one.  Move them
    # all up one space.
    @tracelog
    def frame_up_button_clicked(self, _):
        """Move selected row(s) in the frame plan table up one position"""
        # print("frameUpButtonClicked")
        rows_selected: [int] = self.frame_plan_selected_rows()
        rows_selected.sort()
        assert (len(rows_selected) > 0)
        assert (rows_selected[0] != 0)

        for row_index in rows_selected:
            # To move a row up, we delete it from its current position and insert it one higher
            frame_set_being_moved: FrameSet = self.model.get_frame_set(row_index)
            self._plan_table_model.deleteRow(row_index)
            self._plan_table_model.insertFrameSet(frame_set_being_moved, row_index - 1)
            self.set_is_dirty(True)

        # Re-do the selection so the rows just moved remain selected
        new_selection = map(lambda x: x - 1, rows_selected)
        self.frame_plan_select_rows(new_selection)
        self.enable_controls()

    # One or more lines are selected, not including the bottom one.  Move them
    # all down one space.
    @tracelog
    def frame_down_button_clicked(self, _):
        """Move selected row(s) in the frame plan table down one position"""
        # print("frameDownButtonClicked")
        rows_selected: [int] = self.frame_plan_selected_rows()
        # Handle the rows from bottom of screen upward
        rows_selected.sort(reverse=True)
        assert (len(rows_selected) > 0)  # Can't be here unless something is selected
        assert (rows_selected[0] != len(self.model.get_saved_frame_sets()) - 1)  # Bottom row not allowed

        for row_index in rows_selected:
            # To move a row down, we delete it from its current position and insert it one lower
            #   e.g let's move row 2 down
            #   before:
            #       0:  a
            #       1:  b
            #       2:  c
            #       3:  d
            #   Delete row 2
            #       0:  a
            #       1:  b
            #       2:  d
            #   Insert row 3
            #       0:  a
            #       1:  b
            #       2:  d
            #       3:  c
            frame_set_being_moved: FrameSet = self.model.get_frame_set(row_index)
            self._plan_table_model.deleteRow(row_index)
            self._plan_table_model.insertFrameSet(frame_set_being_moved, row_index + 1)
            self.set_is_dirty(True)

        # Re-do the selection so the rows just moved remain selected
        new_selection = map(lambda x: x + 1, rows_selected)
        self.frame_plan_select_rows(new_selection)
        self.enable_controls()

    @tracelog
    def begin_session_button_clicked(self, _):
        """Begin the dark frame acquisition process"""
        # print("beginSessionButtonClicked")
        self.restrict_session_buttons()
        self.run_session_thread()
        # self.derestrictSessionButtons() when we are signalled that the started session has ended

    # Fill in the table of framesets we'll work on in this session, with the subset of plan
    # framesets that are not complete
    @tracelog
    def populate_session_framesets_table(self):
        """Fill in the table that will show progress of the acquisition process"""
        # print("populateSessionFramesetsTable")
        # Have table columns resize to fit data
        horizontal_header: QHeaderView = self.ui.sessionTable.horizontalHeader()
        horizontal_header.setSectionResizeMode(QHeaderView.ResizeToContents)
        horizontal_header.setStretchLastSection(True)
        # Get framesets to display and set up the table data source
        self._session_framesets = self.model.get_incomplete_framesets()
        self._session_table_model = FrameSetSessionTableModel(self._session_framesets)
        self.ui.sessionTable.setModel(self._session_table_model)

    # Disable all the controls except the Cancel button so the session runs without complicated changes

    @tracelog
    def restrict_session_buttons(self):
        """Disable buttons and tabs that shouldn't be used during frame acquisition"""
        # print("restrictSessionButtons")

        # Disable Begin button on this page and Enable the Cancel button
        self.ui.beginSessionButton.setEnabled(False)
        self.ui.cancelSessionButton.setEnabled(True)

        # Disable the tabs so they can't switch to another page
        for tab_index in range(self.ui.mainTabView.count()):
            if tab_index != MainWindow.RUN_SESSION_TAB_INDEX:
                self.ui.mainTabView.setTabEnabled(tab_index, False)

    # Run the acquisition session as a separate thread so our UI remains responsive
    @tracelog
    def run_session_thread(self):
        """Spawn the sub-thread that does the data acquisition"""
        # print("runSessionThread")
        proceed = True
        if self.model.get_auto_save_after_each_frame():
            # Since we're going to do a save after each frame, we need to make sure
            # that a file to save to is established.
            proceed = self.save_for_session_with_autosave()
            # print(f"Save-autosaved returned proceed= {proceed}")

        if proceed:
            # Controller object to communicate running/cancel  status to worker
            self._thread_controller = SessionController()
            self._mutex = QMutex()
            # Create worker object to do the work of the session

            session_time_info = self.model.get_session_time_info()
            session_temperature_info = self.model.get_session_temperature_info()
            self._worker_object = SessionThreadWorker(self._session_framesets, session_time_info,
                                                      self._thread_controller,
                                                      session_temperature_info,
                                                      self.model.get_send_wake_on_lan_before_starting(),
                                                      self.model.get_send_wol_seconds_before(),
                                                      self.model.getWolBroadcastAddress(),
                                                      self.model.getWolMacAddress(),
                                                      self.model.get_net_address(), int(self.model.get_port_number()),
                                                      self.model.get_disconnect_when_done())
            self._worker_object.consoleLine.connect(self.add_line_to_console_frame)
            self._worker_object.startRowIndex.connect(self.session_started_row_index)
            self._worker_object.startProgressBar.connect(self.start_session_progress_bar)
            self._worker_object.updateProgressBar.connect(self.update_session_progress_bar)
            self._worker_object.displayCameraPath.connect(self.display_camera_path)
            self._worker_object.frameAcquired.connect(self.frame_acquired)
            self._worker_object.coolerStarted.connect(self.cooler_started)
            self._worker_object.coolerStopped.connect(self.cooler_stopped)

            # Create thread and attach worker object to it
            self._qthread = QThread()
            self._worker_object.moveToThread(self._qthread)

            # Have the thread-started signal invoke the actual worker object
            self._qthread.started.connect(self._worker_object.run_session)

            # Have the worker finished signal tell the thread to quit
            self._worker_object.finished.connect(self._qthread.quit)

            # Set up signals to receive signals from the thread
            self._qthread.finished.connect(self.thread_finished)

            # Run the thread
            self._qthread.start()
        else:
            # We didn't go ahead because of "cancel" at file-save.  Clean up as though
            # the thread ran and completed properly
            self.thread_finished()

    @tracelog
    def thread_finished(self):
        """Receive signal that acquisition thread is finished, and clean up"""
        # print("threadFinished")
        self.ui.progressBar.setValue(0)
        self.cooler_stopped()
        self._qthread = None
        self._worker_object = None
        self._thread_controller = None
        self.derestrict_session_buttons()

    # WOrker thread has told us the camera cooler has started.
    # This allows us to set up a timer to display the cooler power
    @tracelog
    def cooler_started(self):
        """Receive signal that camera cooling has started. Set timer to update power display"""
        # print("cooler_started")
        # Get our own instance of the server for talking to TheSkyX
        self._cooling_server = TheSkyX(self.model.get_net_address(), int(self.model.get_port_number()))

        # Set up a timer to update the cooling power display occasionally
        timer = QTimer()
        self._cooler_timer = timer
        timer.timeout.connect(self.cooler_timer_fired)
        # timer.start(5 * 1000)
        timer.start(MainWindow.COOLER_POWER_UPDATE_INTERVAL * 1000)

    @tracelog
    def cooler_timer_fired(self):
        """Periodic timer to update the cooler power display"""
        # print("cooler_timer_fired")
        (success, cooler_power, message) = self._cooling_server.get_cooler_power()
        if success:
            self.ui.coolerPowerLabel.setVisible(True)
            self.ui.coolerPowerValue.setVisible(True)
            self.ui.coolerPowerValue.setText(f"{cooler_power}%")

    # WOrker thread has told us the camera cooler has stopped.
    # This allows us to stop the cooler power timer and remove that display item
    @tracelog
    def cooler_stopped(self):
        """Receive signal that camera cooling has sotpped, stop power timer"""
        # print("cooler_stopped")
        if self._cooler_timer is not None:
            self._cooler_timer.stop()
            self._cooler_timer = None
        self.ui.coolerPowerLabel.setVisible(False)
        self.ui.coolerPowerValue.setVisible(False)
        self._cooling_server = None

    # The worker thread reports that a frame has been successfully acquired.
    # If the option is on, do a save after the acquisition

    @tracelog
    def frame_acquired(self, frame_set: FrameSet, row_index: int):
        """Receive signal that a frame has been acquired. Update number complete"""
        # print(f"frame_acquired.  Frame Set: {frame_set}")
        frame_set.set_number_complete(frame_set.get_number_complete() + 1)
        # Tell the session table model about this change so the on-screen table can update
        self._session_table_model.table_row_changed(row_index)
        if self.model.get_auto_save_after_each_frame():
            self.save_menu_triggered(None)

    @tracelog
    def add_line_to_console_frame(self, message: str, level: int):
        """Receive signal requesting a line be placed in the console frame"""
        # print(f"addLineToConsoleFrame({message})")
        self._mutex.lock()
        time_formatted = strftime("%H:%M:%S ")
        indent_string = ""
        if level > 1:
            indentation_block = " " * MainWindow.INDENTATION_DEPTH
            indent_string = indentation_block * (level - 1)

        # Create the text line to go in the console
        list_item: QListWidgetItem = QListWidgetItem(time_formatted + " " + indent_string + message)

        # Set its font size according to the settings
        item_font: QFont = list_item.font()
        settings = QSettings()
        item_font.setPointSize(settings.value(MultiOsUtil.STANDARD_FONT_SIZE_SETTING))
        list_item.setFont(item_font)

        # Add to bottom of console and scroll to it
        self.ui.consoleList.addItem(list_item)
        self.ui.consoleList.scrollToItem(list_item)
        self._mutex.unlock()

    @tracelog
    def session_started_row_index(self, row_index: int):
        """Receive signal that a new row has started, highlight that row"""
        # print(f"session_started_row_index({row_index})")
        # Select the row in the table corresponding to this index, so it highlights
        self._mutex.lock()
        selection: QItemSelection = QItemSelection()
        model_index_top_left: QModelIndex = self._session_table_model.createIndex(row_index, 0)
        model_index_bottom_right: QModelIndex = \
            self._session_table_model.createIndex(row_index,
                                                  FrameSet.NUMBER_OF_DISPLAY_FIELDS - 1)
        selection.select(model_index_top_left, model_index_bottom_right)
        # Set the selection to that  row
        selection_model: QItemSelectionModel = self.ui.sessionTable.selectionModel()
        selection_model.clearSelection()
        selection_model.select(selection, QItemSelectionModel.Select)
        # Scroll to ensure the selected row is in view
        self.ui.sessionTable.scrollTo(model_index_top_left)
        self._mutex.unlock()

    # self._worker_object.startProgressBar.connect(self.start_session_progress_bar)
    # tracelog
    def start_session_progress_bar(self, bar_maximum: int):
        """Receive signal to turn on and start the progress bar"""
        # print(f"start_session_progress_bar({bar_maximum})")
        self._mutex.lock()
        self.ui.progressBar.setMaximum(bar_maximum)
        self.ui.progressBar.setValue(0)
        self._mutex.unlock()

    # self._worker_object.updateProgressBar.connect(self.update_session_progress_bar)
    # tracelog
    def update_session_progress_bar(self, new_value: int):
        """Receive signal to update the progress bar"""
        # print(f"update_session_progress_bar({new_value})")
        self._mutex.lock()
        self.ui.progressBar.setValue(new_value)
        self._mutex.unlock()

    # Restore the controls that were disabled during the session
    @tracelog
    def derestrict_session_buttons(self):
        """Turn off former restrictions on UI buttons when session thread is done"""
        # print("derestrictSessionButtons")

        # Enable  Begin button on this page, disable Cancel
        self.ui.beginSessionButton.setEnabled(True)
        self.ui.cancelSessionButton.setEnabled(False)

        # Enable the tabs we disabled  before
        for tab_index in range(self.ui.mainTabView.count()):
            if tab_index != MainWindow.RUN_SESSION_TAB_INDEX:
                self.ui.mainTabView.setTabEnabled(tab_index, True)

    @tracelog
    def cancel_session_button_clicked(self, _):
        """Cancel button clicked, set flag to cancel sub-thread"""
        # print("cancelSessionButtonClicked")
        self.add_line_to_console_frame("** Cancel Requested **", 1)
        if self._thread_controller is not None:
            self._thread_controller.cancel_thread()

    @tracelog
    def save_as_menu_triggered(self, _):
        """Save As menu selected - prompt for file name and save file"""
        # print("saveAsMenuTriggered")
        file_name, _ = QFileDialog.getSaveFileName(self,
                                                   "Dark and Bias Frames Plan File",
                                                   "",
                                                   f"FrameSet Plans(*{MainWindow.SAVED_FILE_EXTENSION})")
        if file_name == "":
            # User cancelled from dialog, so don't do the save
            pass
        else:
            with open(file_name, "w") as saving_file:
                saving_file.write(self.model.serialize_to_json())
            self.ui.setWindowTitle(file_name)
            self._file_path = file_name
            self.set_is_dirty(False)

            #  Remember this path in preferences so we come here next time
            settings = QSettings()
            settings.setValue("last_opened_path", file_name)

    # We're about to start a session that has "autosave after each frame" selected.
    # There needs to be a save file established.  If there isn't, use a dialog to ask
    # for one and if it is cancelled, don't do the session
    @tracelog
    def save_for_session_with_autosave(self) -> bool:
        """Before doing a session with autosave, ensure that a save file is established"""
        proceed = False
        # print("save_for_session_with_autosave")
        if self._file_path != "":
            proceed = True
            # We have a file established, no action needed
        else:
            file_name, _ = QFileDialog.getSaveFileName(self,
                                                       "Dark and Bias Frames Plan File",
                                                       "",
                                                       f"FrameSet Plans(*{MainWindow.SAVED_FILE_EXTENSION})")
            if file_name == "":
                # User cancelled from dialog, don't proceed with the session
                proceed = False
            else:
                proceed = True
                self._file_path = file_name
        # print(f"save_for_session_with_autosave returns {proceed}")
        return proceed

    @tracelog
    def save_menu_triggered(self, _):
        """Save Menu selected.  Save file - do Save As if file name not yet known"""
        # print("saveMenuTriggered")
        if self._file_path == "":
            # print("  File not set, treating as SaveAs")
            self.save_as_menu_triggered(None)
        else:
            # print(f"  File known ({self._file_path}, saving again")
            with open(self._file_path, "w") as re_saving_file:
                re_saving_file.write(self.model.serialize_to_json())
            self.set_is_dirty(False)

    @tracelog
    def close_menu_triggered(self, _):
        """Intercept close menu to ensure we don't lose unsaved changes"""
        # print("closeMenuTriggered")
        self.protect_unsaved_close()
        app = QtWidgets.QApplication.instance()
        app.quit()

    @tracelog
    def open_menu_triggered(self, _):
        """Open menu selected - load a saved file"""
        # print("openMenuTriggered")
        #  Get last path from preferences to start the open dialog there
        settings = QSettings()
        last_opened_path = settings.value("last_opened_path")
        if last_opened_path is None:
            last_opened_path = ""

        # Get file name to open
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", last_opened_path,
                                                   f"FrameSet Plans(*{MainWindow.SAVED_FILE_EXTENSION})")
        if file_name != "":
            self.protect_unsaved_close()
            # Read the saved file and load the data model with it
            with open(file_name, "r") as file:
                loaded_model = json.load(file, cls=DataModelDecoder)
                self.model.update_from_loaded_json(loaded_model)

            # Populate window with new data model
            self.accept_data_model(self.model)
            #  Set window title to reflect the opened file
            self.ui.setWindowTitle(file_name)
            #  Just loaded the data, so it can't be dirty yet
            self.set_is_dirty(False)
            #  Remember the file path so plain "save" works.
            self._file_path = file_name

            #  Remember this path in preferences so we come here next time
            settings.setValue("last_opened_path", file_name)

    @tracelog
    def new_menu_triggered(self, _):
        """NEW menu selected - open a new plan with default values"""
        # print("newMenuTriggered")
        # Protected save
        self.protect_unsaved_close()
        # Get a new data model with default values, load those defaults into
        # the in-use model
        new_model = DataModel()
        self.model.load_from_model(new_model)
        # Populate window
        self.accept_data_model(self.model)
        # Set window title to unsaved
        self.ui.setWindowTitle(self.UNSAVED_WINDOW_TITLE)
        self.set_is_dirty(False)

    @tracelog
    def app_about_to_quit(self):
        """Intercept application quit to ensure we don't lose unsaved changes"""
        # print("appAboutToQuit")
        self.protect_unsaved_close()

    # We're about to close or quit.  If there is unsaved data, ask the user
    # if they want to save it before continuing with the close or quit
    @tracelog
    def protect_unsaved_close(self):
        """IF there are unsaved changes, give user a chance to save them"""
        # print("protectUnsavedClose")
        if self.is_dirty():
            # print("   File is dirty, check if save wanted")
            message_dialog = QMessageBox()
            message_dialog.setWindowTitle("Unsaved Changes")
            message_dialog.setText("You have unsaved changes")
            message_dialog.setInformativeText("Would you like to save the file or discard these changes?")
            message_dialog.setStandardButtons(QMessageBox.Save | QMessageBox.Discard)
            message_dialog.setDefaultButton(QMessageBox.Save)
            dialog_result = message_dialog.exec_()
            # print(f"   Dialog returned {dialog_result}")
            if dialog_result == QMessageBox.Save:
                # print("      SAVE button was pressed")
                self.save_menu_triggered(None)
            else:
                # print("      DISCARD button was pressed")
                # Since they don't want to save, consider the document not-dirty
                self.set_is_dirty(False)
        else:
            # print("   File is not dirty, allow close to proceed")
            pass

    # Info about frame plan table
    @tracelog
    def frame_plan_selected_rows(self) -> [int]:
        """Return list of indices of rows selected in frame plan table"""
        selection_model: QItemSelectionModel = self.ui.framesPlanTable.selectionModel()
        indices: List[QModelIndex] = selection_model.selectedRows()
        selected_rows = []
        for index in indices:
            selected_rows.append(index.row())
        return selected_rows

    # Select the given row indices in the frame plan table
    @tracelog
    def frame_plan_select_rows(self, indices: List[int]):
        """Select specified row(s) in frame plan table"""
        # Make up an item selection object for the rows in question, and all the columns
        selection: QItemSelection = QItemSelection()
        for row_index in indices:
            model_index_top_left: QModelIndex = self._plan_table_model.createIndex(row_index, 0)
            model_index_bottom_right: QModelIndex = self._plan_table_model.createIndex(row_index,
                                                                                       FrameSet.NUMBER_OF_DISPLAY_FIELDS - 1)
            # Extend selection to include this row
            selection.select(model_index_top_left, model_index_bottom_right)

        # Set the selection to that list of rows
        selection_model: QItemSelectionModel = self.ui.framesPlanTable.selectionModel()
        selection_model.clearSelection()
        selection_model.select(selection, QItemSelectionModel.Select)

    # If start or end times are set to be sun-based, calculate the time and put in the message
    @tracelog
    def calculate_sun_based_times(self):
        """Calculate sunrise/sunset-based times and place in display fields"""
        # print("calculateSunBasedTimes")
        # Start time
        start_time_type: str = self.model.get_start_time_type()
        start_date_type: str = self.model.get_start_date_type()
        given_start_date: str = DataModel.parse_date(self.model.get_given_start_date())
        if start_time_type == StartTime.SUNSET:
            sunset_time: time = self.model.calc_sunset(start_date_type, given_start_date)
            self.ui.calculatedStartTime.setText(sunset_time.strftime("Sunset: %H:%M"))
        elif start_time_type == StartTime.CIVIL_DUSK:
            civil_dusk: time = self.model.calc_civil_dusk(start_date_type, given_start_date)
            self.ui.calculatedStartTime.setText(civil_dusk.strftime("C.Dusk: %H:%M"))
        elif start_time_type == StartTime.NAUTICAL_DUSK:
            nautical_dusk: time = self.model.calc_nautical_dusk(start_date_type, given_start_date)
            self.ui.calculatedStartTime.setText(nautical_dusk.strftime("N.Dusk: %H:%M"))
        elif start_time_type == StartTime.ASTRONOMICAL_DUSK:
            astronomical_dusk: time = self.model.calc_astronomical_dusk(start_date_type, given_start_date)
            self.ui.calculatedStartTime.setText(astronomical_dusk.strftime("A.Dusk: %H:%M"))
        else:
            assert (start_time_type == StartTime.GIVEN_TIME)
            self.ui.calculatedStartTime.setText("")

        # End time
        end_time_type: str = self.model.get_end_time_type()
        end_date_type: str = self.model.get_end_date_type()
        given_end_date: date = DataModel.parse_date(self.model.get_given_end_date())
        if end_time_type == EndTime.SUNRISE:
            sunrise_time: time = self.model.calc_sunrise(end_date_type, given_end_date)
            self.ui.calculatedEndTime.setText(sunrise_time.strftime("Sunrise: %H:%M"))
        elif end_time_type == EndTime.CIVIL_DAWN:
            civil_dawn: time = self.model.calc_civil_dawn(end_date_type, given_end_date)
            self.ui.calculatedEndTime.setText(civil_dawn.strftime("C.Dawn: %H:%M"))
        elif end_time_type == EndTime.NAUTICAL_DAWN:
            nautical_dawn: time = self.model.calc_nautical_dawn(end_date_type, given_end_date)
            self.ui.calculatedEndTime.setText(nautical_dawn.strftime("N.Dawn: %H:%M"))
        elif end_time_type == EndTime.ASTRONOMICAL_DAWN:
            astronomical_dawn: time = self.model.calc_astronomical_dawn(end_date_type, given_end_date)
            self.ui.calculatedEndTime.setText(astronomical_dawn.strftime("A.Dawn: %H:%M"))
        else:
            assert (end_time_type == EndTime.GIVEN_TIME)
            self.ui.calculatedEndTime.setText("")

    # The main window tab view tab has changed.
    # See if we've just entered the "run session" tab so we can populate the table
    @tracelog
    def tab_view_tab_changed(self, selected_index):
        """Respond to main tab being changed, populate session table if session tab"""
        # print(f"tabViewTabChanged: {selected_index}")
        if selected_index == self.RUN_SESSION_TAB_INDEX:
            # print("Run Session tab entered")
            self.populate_session_framesets_table()

    # Receive the camera autosave path from the network client, and display in the UI
    @tracelog
    def display_camera_path(self, autosave_path: str):
        """Receive signal giving server's path to auto save files, display it in session window"""
        self._mutex.lock()
        self.ui.cameraPath.setText(autosave_path)
        self._mutex.unlock()

    # Catch window resizing so we can record the changed size

    def eventFilter(self, object: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Resize:
            window_size = event.size()
            # height = event.size().height()
            # width = event.size().width()
            settings = QSettings()
            settings.setValue(MultiOsUtil.LAST_WINDOW_SIZE_SETTING, window_size)
        return False  # Didn't handle event

    # Menu to enlarge font size (by one point) in the window
    @tracelog
    def font_size_larger(self, _):
        self.increment_font_size(self.ui, increment=+1)

    # Menu to reduce font size (by one point) in the window
    @tracelog
    def font_size_smaller(self, _):
        self.increment_font_size(self.ui, increment=-1)

    @tracelog
    def increment_font_size(self, parent: QObject, increment: int):
        settings = QSettings()
        old_standard_font_size = settings.value(MultiOsUtil.STANDARD_FONT_SIZE_SETTING)
        new_standard_font_size = old_standard_font_size + increment
        settings.setValue(MultiOsUtil.STANDARD_FONT_SIZE_SETTING, new_standard_font_size)
        MultiOsUtil.set_font_sizes(parent=parent,
                                   standard_size = new_standard_font_size,
                                   title_prefix = MultiOsUtil.MAIN_TITLE_LABEL_PREFIX,
                                   title_increment=MultiOsUtil.MAIN_TITLE_FONT_SIZE_INCREMENT,
                                   subtitle_prefix=MultiOsUtil.SUBTITLE_LABEL_PREFIX,
                                   subtitle_increment=MultiOsUtil.SUBTITLE_FONT_SIZE_INCREMENT)

    @tracelog
    def font_size_reset(self, _):
        settings = QSettings()
        settings.setValue(MultiOsUtil.STANDARD_FONT_SIZE_SETTING, MultiOsUtil.STANDARD_FONT_SIZE)
        MultiOsUtil.set_font_sizes(parent=self.ui,
                                   standard_size=MultiOsUtil.STANDARD_FONT_SIZE,
                                   title_prefix=MultiOsUtil.MAIN_TITLE_LABEL_PREFIX,
                                   title_increment=MultiOsUtil.MAIN_TITLE_FONT_SIZE_INCREMENT,
                                   subtitle_prefix=MultiOsUtil.SUBTITLE_LABEL_PREFIX,
                                   subtitle_increment=MultiOsUtil.SUBTITLE_FONT_SIZE_INCREMENT)

    # Set the flag that tracelog uses to dump call/exit info
    def write_trace_info_clicked(self):
        settings = QSettings()
        settings.setValue(TRACE_LOG_SETTING, self.ui.writeTraceInfo.isChecked())

    # TODO Change to "red field" validation notice, as in Flats program