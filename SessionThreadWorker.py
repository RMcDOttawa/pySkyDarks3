from datetime import datetime, timedelta
from time import sleep

from PyQt5.QtCore import QObject, pyqtSignal

from BiasFrameSet import BiasFrameSet
from CameraCoolingInfo import CameraCoolingInfo
from DarkFrameSet import DarkFrameSet
from FrameSet import FrameSet
from RmNetUtils import RmNetUtils
from SessionController import SessionController
from SessionTimeInfo import SessionTimeInfo
from TheSkyX import TheSkyX


class SessionThreadWorker(QObject):
    PROGRESS_UPDATE_INTERVAL = 2  # Update progress bar every this many seconds
    CAMERA_RESYNC_CHECK_INTERVAL = .5  # After camera should be done, check in every this many seconds
    CAMERA_RESYNC_TIMEOUT = 3 * 60  # Time out if camera doesn't resync after this many seconds

    finished = pyqtSignal()
    startRowIndex = pyqtSignal(int)
    consoleLine = pyqtSignal(str, int)
    startProgressBar = pyqtSignal(int)  # Initialize progress bar, for maximum this much
    updateProgressBar = pyqtSignal(int)  # Update the bar with this value of progress toward maximum
    displayCameraPath = pyqtSignal(str)  # Display given camera autosave path in the UI
    frameAcquired = pyqtSignal(FrameSet, int)  # A frame has been successfully acquired
    coolerStarted = pyqtSignal()  # Tell main UI that we are running the cooler
    coolerStopped = pyqtSignal()  # Tell main UI that we have stopped the cooler

    def __init__(self,
                 frame_set_list: [FrameSet],  # Frames to be acquired
                 time_info: SessionTimeInfo,  # start and end time info
                 controller: SessionController,  # inter-process signaling controller
                 cooling_info: CameraCoolingInfo,
                 wake_on_lan_before: bool,  # send a WOL before starting?
                 wake_on_lan_lead_seconds: float,  # how long in advance to send WOL?
                 wol_broadcast_address: str,
                 wol_mac_address: str,
                 network_address: str,
                 network_port: int,
                 disconnect_when_done: bool):
        # print(f"SessionThreadWorker init called with timeInfo {time_info}")
        QObject.__init__(self)
        self._frame_set_list: [FrameSet] = frame_set_list
        self._time_info: SessionTimeInfo = time_info
        self._controller: SessionController = controller
        self._cooling_info: CameraCoolingInfo = cooling_info
        self._wake_on_lan_before: bool = wake_on_lan_before
        self._wake_on_lan_lead_seconds: float = wake_on_lan_lead_seconds
        self._wol_broadcast_address: str = wol_broadcast_address
        self._wol_mac_address: str = wol_mac_address
        self._network_address: str = network_address
        self._network_port: int = network_port
        self._disconnect_when_done = disconnect_when_done

        self._download_times: {int: float} = {}  # We'll measure times of binnings later

    def run_session(self):
        # print("SessionThreadWorker/run_session")
        self.console("Starting session", 1)
        normal_completion = False
        if self.wait_for_start_time(self._time_info.get_start_now(),
                                    self._time_info.get_start_date_time(),
                                    self._wake_on_lan_before, self._wake_on_lan_lead_seconds):
            if self.optional_wake_on_lan(self._wake_on_lan_before, self._wake_on_lan_lead_seconds,
                                         self._wol_broadcast_address, self._wol_mac_address):
                server = TheSkyX(self._network_address, self._network_port)
                (success, path, message) = self.get_camera_path(server)
                if not success:
                    self.console("Unable to connect to TheSkyX server", 1)
                    self.console("Message: " + message, 2)
                else:
                    self.displayCameraPath.emit(path)
                    if self.connect_to_camera(server):
                        if self.start_cooling_camera(server, self._cooling_info):
                            # Now that the camera cooler is on (if it is cooled), start a timer that
                            # will update the displayed cooler power every so often
                            started_cooling_at = datetime.now()
                            if self.measure_download_times(server):
                                if self.wait_for_cooling(server, self._cooling_info, started_cooling_at):
                                    if self.acquire_frames(server, self._frame_set_list,
                                                           self._cooling_info, self._time_info):
                                        if self.warmup_if_requested(server, self._cooling_info):
                                            if self.disconnect_if_requested(server, self._disconnect_when_done):
                                                normal_completion = True
        if normal_completion:
            self.console("Session completed normally", 1)
        else:
            self.console("Session cancelled or failed", 1)
        self.finished.emit()
        # print("run_session Ended")

    # Wait until an appropriate start time.
    #  This might be
    #       - No wait (start now); or
    #       - Wait until a given time, optionally reduced by Wake-On-Lan lead time
    # return a success indicator
    def wait_for_start_time(self, start_now: bool, start_time: datetime,
                            wake_on_lan_before: bool, wake_on_lan_lead_seconds: float) -> bool:
        # print(f"wait_for_start_time({start_now},{start_time},{wake_on_lan_before},{wake_on_lan_lead_seconds})")
        success = True
        wait_seconds = self.start_wait_seconds(start_now, start_time, wake_on_lan_before, wake_on_lan_lead_seconds)
        if wait_seconds > 0:
            self.console(f"Waiting {self.casual_interval_format(wait_seconds)}", 1)
            success = self.sleep_with_progress_bar(wait_seconds)
        return success

    @staticmethod
    def start_wait_seconds(start_now: bool, start_time: datetime,
                           wake_on_lan_before: bool, wake_on_lan_lead_seconds: float) -> float:
        # print(f"start_wait_seconds({start_now},{start_time},{wake_on_lan_before},{wake_on_lan_lead_seconds})")
        # Start with how long to wait
        if start_now:
            wait_time = 0
        else:
            difference = start_time - datetime.now()
            wait_time = difference.seconds
        # print(f"Initial start delay = {wait_time} seconds")

        # If wake-on-lan is wanted in advance, reduce wait time by that much to leave time for it
        if wake_on_lan_before:
            wait_time -= wake_on_lan_lead_seconds
            # print(f"  Reducing for WOL by {wake_on_lan_lead_seconds} give {wait_time} seconds")

        # If we've reduced the wait time below zero, just use zero; we'll start right away,
        # and run a little late after the Wake-on-lan time
        if wait_time < 0:
            wait_time = 0
            # print("  Chopped reduced wait time off at zero")

        return wait_time

    @staticmethod
    def casual_interval_format(seconds: float) -> str:
        # print(f"casual_interval_format({seconds})")
        hours_string = ""
        minutes_string = ""
        seconds_string = ""
        seconds_in_hour = 60 * 60
        if seconds > seconds_in_hour:
            hours: int = round(seconds) // seconds_in_hour
            seconds -= hours * seconds_in_hour
            hours_string = str(hours) + " hour" + ("s" if hours > 1 else "")

        if seconds > 60:
            minutes: int = round(seconds) // 60
            seconds -= minutes * 60
            minutes_string = str(minutes) + " minute" + ("s" if minutes > 1 else "")

        seconds = int(round(seconds))
        if seconds > 0:
            seconds_string = str(seconds) + " second" + ("s" if seconds > 1 else "")

        result = hours_string
        if minutes_string != "":
            minutes_addendum = (", " if result != "" else "") + minutes_string
            result = result + minutes_addendum
        if seconds_string != "":
            seconds_addendum = (", " if result != "" else "") + seconds_string
            result = result + seconds_addendum

        return result

    # Sleep the given number of seconds, emitting a signal to let the
    # main UI window update a progress bar.   Because we want to update the
    # progress bar periodically, we don't just do a sleep for the total number
    # of seconds.  Instead, we sleep in small increments and keep watch on the
    # current time and the time we need to finish the sleep.
    # we normally use this function (rather than the no-progress-bar version) for longer
    # sleeps such as waiting for the camera to cool.  So the fact that the sleep may exceed
    # the requested amount by "update_interval" (2 seconds) is not a concern
    def sleep_with_progress_bar(self, wait_seconds: float) -> bool:
        # print(f"sleep_with_progress_bar({wait_seconds})")
        self.startProgressBar.emit(int(round(wait_seconds)))
        # What time is the sleep finished?
        time_finished = datetime.now() + timedelta(seconds=wait_seconds)
        accumulated_seconds = 0
        while (datetime.now() <= time_finished) and self._controller.thread_running():
            # QThread.sleep(SessionThreadWorker.PROGRESS_UPDATE_INTERVAL)
            sleep(SessionThreadWorker.PROGRESS_UPDATE_INTERVAL)
            accumulated_seconds += SessionThreadWorker.PROGRESS_UPDATE_INTERVAL
            self.updateProgressBar.emit(accumulated_seconds)
        return self._controller.thread_running()

    # Do some console activity as a simulation of a session
    def session_simulator(self, minutes: float):
        stub_total_sleep_length = minutes * 60
        stub_message_interval = 1
        self.console(f"session twiddling for {stub_total_sleep_length} seconds", 1)
        accumulated_time = 0
        while accumulated_time < stub_total_sleep_length and self._controller.thread_running():
            # QThread.sleep(stub_message_interval)
            sleep(stub_message_interval)
            accumulated_time += stub_message_interval
            self.console(f"... {accumulated_time}", 2)
        if self._controller.thread_running():
            self.console("twiddle ended", 1)
            success = True
        else:
            self.console("session cancelled", 1)
            success = False
        return success

    # Emit a string to the console slot, so the main UI thread will pick it up
    # and add it to the console pane

    def console(self, message: str, level: int):
        self.consoleLine.emit(message, level)

    # If requested, send wake-on-lan broadcast packet and then wait a given time interval
    # return an all-is-well indicator

    def optional_wake_on_lan(self, wake_requested: bool, wake_wait_time: float,
                             broadcast_address: str, mac_address: str):
        # print(f"optional_wake_on_lan({wake_requested},{wake_wait_time},{broadcast_address},{mac_address})")
        success = True
        if wake_requested:
            self.console("Sending Wake-On-Lan", 1)
            (success, message) = RmNetUtils.send_wake_on_lan(broadcast_address, mac_address)
            if not success:
                self.console("Wake on LAN error: " + message, 2)
            else:
                self.console("Wake sent.  Waiting " + self.casual_interval_format(wake_wait_time), 2)
                success = self.sleep_with_progress_bar(wake_wait_time)
        return success

    # Connect to TheSkyX as a connection test and, while we're at it, get and return the camera autosave path
    @staticmethod
    def get_camera_path(server: TheSkyX) -> (bool, str):
        # print(f"get_camera_path()")
        (success, path, message) = server.get_camera_autosave_path()
        return success, path, message

    # Have TheSkyX connect to the camera
    def connect_to_camera(self, server: TheSkyX) -> bool:
        # self.console("Connecting to camera",1)
        (success, message) = server.connect_to_camera()
        if not success:
            self.console(f"Error connecting: {message}", 2)
        return success

    def start_cooling_camera(self, server: TheSkyX, cooling_info: CameraCoolingInfo) -> bool:
        # print("start_cooling_camera")
        success = True
        if cooling_info.is_regulated:
            # Camera is regulated, so we'll start cooling toward the target
            self.console(f"Start cooling camera to target {cooling_info.target_temperature}", 1)
            (success, message) = server.set_camera_cooling(True, cooling_info.target_temperature)
            if success:
                self.coolerStarted.emit()
            else:
                self.console("Error starting camera cooling", 2)
                self.console(f"Message: {message}", 2)
        # print(f"start_cooling_camera exits")
        return success

    # Measure how long downloads take for all the binning-values in the list of frames
    # Do this by taking a bias frame at each binning.
    # Record in dictionary self._download_times: {int:float}, return a success flag
    def measure_download_times(self, server: TheSkyX) -> bool:
        # print("measure_download_times entered")
        self.console("Measuring download times", 1)
        success = True
        for frame_set in self._frame_set_list:
            if self._controller.thread_cancelled():
                success = False
                break
            binning = frame_set.get_binning()
            if binning not in self._download_times:
                (success, download_seconds) = self.time_download(server, binning)
                if not success:
                    break
                self._download_times[binning] = download_seconds
        # print(f"measure_download_times exits {success}")
        # print(self._download_times)
        return success

    # Time download for given binning.  Return seconds taken and a success indicator
    def time_download(self, server: TheSkyX, binning: int) -> (bool, float):
        # print(f"time_download({binning})")
        seconds = -1.0
        time_before: datetime = datetime.now()
        (success, message) = server.take_bias_frame(binning, auto_save_file=False, asynchronous=False)
        if success:
            time_after: datetime = datetime.now()
            time_to_download: timedelta = time_after - time_before
            seconds = time_to_download.seconds
            self.console(f"Binned {binning} x {binning}: {seconds} seconds", 2)
        else:
            self.console(f"Error timing download: {message}", 2)
        return success, seconds

    # Wait for the cooling target to be reached.  We wait a maximum amount of time then assume we're not going
    # to reach the target (ambient is too high for the camera's cooler).  If this happens, we can optionally
    # switch off the cooling, wait a period of time, and try again.  The idea is that the ambient temperature
    # is dropping as night falls, and the cooling may succeed after a time.  We retry a given maximum number
    # of times before giving up entirely.
    # Note that for the first attempt, we have already waited a bit while measuring download times, so we
    # take this into account in the first wait cycle.

    def wait_for_cooling(self, server: TheSkyX, cooling_info: CameraCoolingInfo, time_started: datetime) -> bool:
        # print(f"wait_for_cooling (started at {time_started})")
        self.console(f"Waiting for camera to cool to {cooling_info.target_temperature} degrees", 1)
        if cooling_info.is_regulated:
            success = False
            already_waited: float = (datetime.now() - time_started).seconds
            # print(f"   Already waited {already_waited} seconds")
            time_to_wait = max(cooling_info.max_time_to_try - already_waited, 0)
            total_attempts = 1 + cooling_info.cooling_retry_count
            attempt_number = 0
            error = False
            while total_attempts > 0 and (not error) and self._controller.thread_running():
                total_attempts -= 1
                attempt_number += 1
                (success, error) = self.one_cooling_attempt(server,
                                                            cooling_info.target_temperature,
                                                            cooling_info.cooling_check_interval,
                                                            cooling_info.target_tolerance,
                                                            time_to_wait)
                if success or error:
                    # We did it, no further attempts needed;
                    # or, a system error has occurred, just give up and pass the error upward
                    break
                else:
                    # Failed to cool to target.  Turn off cooling
                    self.stop_cooling(server, cooling_info)
                    # If more attempts are remaining, wait the specified time before trying again
                    if total_attempts > 0 and self._controller.thread_running():
                        self.console(
                            f"Cooling failed to reach target temperature of {cooling_info.target_temperature}"
                            + f" after {cooling_info.max_time_to_try} seconds.",
                            1)
                        self.console(
                            f"Waiting {cooling_info.cooling_retry_delay} seconds before attempt {attempt_number + 1}",
                            2)
                        self.sleep_with_progress_bar(cooling_info.cooling_retry_delay)
                        if self._controller.thread_running():
                            time_to_wait = cooling_info.max_time_to_try
                            self.start_cooling_camera(server, cooling_info)

            if not success and self._controller.thread_running():
                self.console("Failed to cool to target temperature", 1)
        else:
            success = True  # Not temp regulated, so we just succeed
        return success

    # Make a single attempt to cool the chip to the target temperature.
    # Check the temperature at regular intervals.  Consider it success if we get within a given tolerance
    # of the target.  If we don't reach the target after a given time, fail
    # Return two flags.  One is whether we cooled successfully (might not have but no error), 2nd is an error

    def one_cooling_attempt(self, server: TheSkyX,
                            target_temperature: float,
                            cooling_check_interval: float,
                            target_tolerance: float,
                            time_to_wait: float) -> (bool, bool):
        # print(f"one_cooling_attempt({target_temperature},{cooling_check_interval},{target_tolerance},{time_to_wait})")
        # Start progress bar for the total of the max duration
        self.startProgressBar.emit(int(round(time_to_wait)))

        # Loop until maximum duration reached or success achieved
        success: bool = False
        error: bool = False
        time_waited: float = 0
        while (time_waited < time_to_wait) and self._controller.thread_running() and not success:
            # Camera is cooling, wait a bit before checking temperature.
            self.sleep_no_progress_bar(cooling_check_interval)
            time_waited += cooling_check_interval
            self.updateProgressBar.emit(int(round(time_waited)))
            (read_temp_successfully, current_camera_temperature, message) = server.get_camera_temperature()
            if read_temp_successfully:
                self.console(f"Camera temperature: {current_camera_temperature}", 2)
                temperature_difference = abs(current_camera_temperature - target_temperature)
                if temperature_difference <= target_tolerance:
                    success = True
                    self.console("Target temperature reached", 2)
                else:
                    # We're cooling but haven't reached the target yet, let the loop continue
                    pass
            else:
                # error in reading camera temperature, fail out of loop
                self.console(f"Error reading temperature: {message}", 2)
                error = True
                break
        return success, error

    # Sleep for the given amount of time.  No progress bar signals emitted.
    # Sleep in little increments, not one big hunk, and check if this thread
    # has been cancelled between increments.
    def sleep_no_progress_bar(self, sleep_time: float):
        time_slept = 0
        while time_slept < sleep_time and self._controller.thread_running():
            # Sleep a chunk of time, or the remaining time, whichever is smaller
            time_remaining = sleep_time - time_slept
            if time_remaining >= SessionThreadWorker.PROGRESS_UPDATE_INTERVAL:
                time_to_sleep = SessionThreadWorker.PROGRESS_UPDATE_INTERVAL
            else:
                time_to_sleep = time_remaining
            sleep(time_to_sleep)
            time_slept += time_to_sleep

    def stop_cooling(self, server: TheSkyX, cooling_info: CameraCoolingInfo) -> bool:
        print("stop_cooling")
        if cooling_info.is_regulated:
            (success, message) = server.set_camera_cooling(False, 0)
            if success:
                self.coolerStopped.emit()
            else:
                self.console("Error stopping camera cooling", 2)
                self.console(f"Message: {message}", 2)
        else:
            success = True
        return success

    # Acquire the dark and bias frames in the list until some reason to end
    # Reasons to end include:
    #   All frames in the list are acquired
    #   Specified end-time is reached (predict this and don't acquire a frame that would exceed it)
    #   Temperature of CCD rises above given threshold
    #   Session cancelled
    #   Error
    # Return an indicator of a normal (non-error) completion.
    # While the acquisition session is running, keep the UI informed of our progress
    # via console lines and highlighting the frameset being worked.
    # After each frame, tell the UI we have finished one so it can do a save if desired

    def acquire_frames(self,
                       server: TheSkyX,
                       frame_set_list: [FrameSet],
                       cooling_info: CameraCoolingInfo,
                       time_info: SessionTimeInfo) -> bool:
        # print(f"acquire_frames entered")
        success = False
        # Use a for-loop because we need the row number
        for row_index in range(len(frame_set_list)):
            self.startRowIndex.emit(row_index)
            frame_set = frame_set_list[row_index]
            # print(f"  Acquiring #{row_index}: {frame_set}")
            if self._controller.thread_cancelled():
                self.console("Image acquisition cancelled", 1)
                success = False
            if self.end_time_exceeded(time_info):
                # self.console("Session end-time has passed, stopping session", 1)
                success = True
                break
            if self.temperature_has_risen_too_much(server, cooling_info):
                # print("Stopping acquisition by temperature rising")
                success = False
                break
            (success, continue_acquisition) = self.acquire_frame_set(server, frame_set, row_index, cooling_info,
                                                                     time_info)
            if success:
                # print("Frame Set acquired successfully")
                if not continue_acquisition:
                    break
            else:
                success = False
                break
        if self._controller.thread_cancelled():
            self.abort_image_from_cancellation(server)
        # print(f"acquire_frames exits: {success}")
        return success

    #   We have stopped the imaging process because the user clicked "cancel".
    #   The camera doesn't know that and might still be imaging.  In fact, it almost certainly is.
    #   Check if image is still in progress and send an Abort if so
    def abort_image_from_cancellation(self, server):
        # print("abort_image_from_cancellation")
        (command_success, is_complete, message) = server.get_exposure_is_complete()
        if command_success and not is_complete:
            server.abort_image()

    #   Has the end time of this session been exceeded?
    def end_time_exceeded(self, time_info: SessionTimeInfo) -> bool:
        # print("end_time_exceeded")
        if time_info.get_end_when_done():
            # print("  We're doing \"end when done\", so time can never be exceeded.")
            time_exceeded = False
        else:
            now = datetime.now()
            # print(f"   Now: {now}, end time: {time_info.get_end_date_time()}")
            time_exceeded = now > time_info.get_end_date_time()

        # print(f"end_time_exceeded returning {time_exceeded}")
        return time_exceeded

    #  Has the camera temperature risen more than allowed?  This could happen if the
    #  ambient temperature is high and the camera and other electronics are emitting enough
    #  heat that the cooler can't keep up.
    def temperature_has_risen_too_much(self, server: TheSkyX, cooling_info: CameraCoolingInfo) -> bool:
        # print("temperature_has_risen_too_much")
        if cooling_info.is_regulated and cooling_info.abort_on_temperature_rise:
            (success, temperature, error) = server.get_camera_temperature()
            if success:
                if (temperature - cooling_info.target_temperature) > cooling_info.abort_temperature_threshold:
                    self.console(
                        f"Camera temp {temperature} exceeds target {cooling_info.target_temperature}"
                        + f"by more than {cooling_info.abort_temperature_threshold}",
                        1)
                    risen_too_much = True
                else:
                    # print("Temp is in range, all is well")
                    risen_too_much = False
            else:
                self.console("Error reading temperature: " + error, 1)
                risen_too_much = True
        else:
            # print("Not using temperature rise abort")
            risen_too_much = False

        return risen_too_much

    #            if self.acquire_frame_set(server, frame_set, cooling_info, time_info):
    #   Acquire one frameset (which is multiple identical frames)
    #   Reasons to stop:
    #       All frames in this set acquired
    #       Time to take the next frame would exceed the end time of the session
    #       Session cancelled
    #       CCD temperature has risen too much
    #       Error
    def acquire_frame_set(self, server: TheSkyX,
                          frame_set: FrameSet,
                          row_index: int,
                          cooling_info: CameraCoolingInfo,
                          time_info: SessionTimeInfo) -> (bool, bool):
        # print("acquire_frame_set")
        continue_acquisition = True

        # How many do we need (give credit for frames already completed)?
        number_needed = frame_set.get_number_of_frames() - frame_set.get_number_complete()
        remember_number_needed = number_needed
        exposure_seconds = 0 if isinstance(frame_set, BiasFrameSet) else frame_set.get_exposure_seconds()
        binning = frame_set.get_binning()

        # Console what we're going to do
        first_part = f"Take {number_needed} {frame_set.type_name_text()} frames"
        if isinstance(frame_set, DarkFrameSet):
            exposure_part = f" of {exposure_seconds} seconds"
        else:
            exposure_part = ""
        last_part = f", binned {binning} x {binning}"
        self.console(first_part + exposure_part + last_part, 1)
        # Set up camera for these identical frames
        (success, message) = server.set_camera_image(frame_set.camera_image_type_code(),
                                                     binning, exposure_seconds)
        if success:
            # Loop thru required number of frames
            success = True
            frame_count = 0
            while (number_needed > 0) and success and continue_acquisition and self._controller.thread_running():
                number_needed -= 1
                # See if this frame would push beyond the desired end time
                if self.frame_would_exceed_end_time(frame_set, time_info):
                    self.console("Frame would extend past session end time.", 2)
                    success = True
                    continue_acquisition = False
                else:
                    # See if the temperature is OK
                    if self.temperature_has_risen_too_much(server, cooling_info):
                        success = False
                    else:
                        # Acquire one image
                        frame_count += 1
                        self.console(f"Acquiring frame {frame_count} of {remember_number_needed}", 2)
                        success = self.acquire_one_frame(server, frame_set, row_index)
            if self._controller.thread_cancelled():
                success = False
        else:
            self.console(f"Error setting camera: {message}", 1)
            success = False
        return success, continue_acquisition

    # Estimate whether taking the specified image frame would exceed the session end time.
    # If end time is "when done" then exceeds is always False.  Otherwise combine the exposure
    # time and download time and calculate what time such a frame would finish.

    def frame_would_exceed_end_time(self,
                                    frame_set: FrameSet,
                                    time_info: SessionTimeInfo) -> bool:
        # print(f"frame_would_exceed_end_time({frame_type},{binning},{exposure})")
        if time_info.get_end_when_done():
            # print("  Not using end time, can't exceed it")
            would_exceed = False
        else:
            total_exposure_time = self.calc_total_exposure_time(frame_set)
            now = datetime.now()
            end_time = now + timedelta(seconds=total_exposure_time)
            if end_time > time_info.get_end_date_time():
                # print("  This exposure would run past the end time")
                would_exceed = True
            else:
                # print("  Exposure would fit in the end time, not exceed it")
                would_exceed = False
        return would_exceed

    # Calculate how long the given exposure would take, including download time
    def calc_total_exposure_time(self, frame_set: FrameSet) -> float:
        # print(f"calc_total_exposure_time({frame_type},{binning},{exposure})")
        exposure_length = 0 if isinstance(frame_set, BiasFrameSet) else frame_set.get_exposure_seconds()
        total_time = exposure_length + self._download_times[frame_set.get_binning()]
        # print(f"calc_total_exposure_time returning {total_time}")
        return total_time

    def acquire_one_frame(self, server: TheSkyX, frame_set: FrameSet, row_index: int) -> bool:
        # print("acquire_one_frame")
        # We want to acquire asynchronously so we can be alert for session cancel
        # Calculate how long image is likely to take
        total_time = self.calc_total_exposure_time(frame_set)
        # Start acquisition asynchronously.  Exposure settings are already set
        (started_ok, message) = server.start_image_asynchronously()
        if started_ok:
            # Wait until image is probably finished, in small increments checking for cancellation
            # print(f"Exposure {frame_set.get_exposure_seconds()}, total wait time={total_time}")
            self.sleep_with_progress_bar(total_time)
            if self._controller.thread_running():
                # Exposure probably done, or close to it. Now re-sync with camera
                (resync_ok, message) = self.wait_for_camera_completion(server)
                if resync_ok:
                    # We have successfully completed an image.  Tell the main thread
                    # print(f"Emiting frameAcquired: {frame_set}")
                    self.frameAcquired.emit(frame_set, row_index)
                    success = True
                else:
                    self.console(f"Error from camera: {message}", 2)
                    success = False
            else:
                # thread was cancelled while waiting for the exposure to complete.
                # we'll stop execution, but no message needed
                success = False
        else:
            self.console(f"Unable to start image: {message}", 2)
            success = False
        return success

    # We have an image acquisition underway (started asynchronously) and almost complete
    # Now we wait for the camera to finish and check that imaging was successful
    #                 (resync_ok, message) = self.wait_for_camera_completion(server)
    # We ask the server if the exposure is complete.  If not, wait a brief time and ask again.
    # repeat for a maximum timeout period, then give up
    def wait_for_camera_completion(self, server) -> (bool, str):
        # print("wait_for_camera_completion")
        success = False
        total_time_waiting = 0.0
        (complete_check_successful, is_complete, message) = server.get_exposure_is_complete()
        while self._controller.thread_running() \
                and complete_check_successful \
                and not is_complete \
                and total_time_waiting < SessionThreadWorker.CAMERA_RESYNC_TIMEOUT:
            sleep(SessionThreadWorker.CAMERA_RESYNC_CHECK_INTERVAL)
            total_time_waiting += SessionThreadWorker.CAMERA_RESYNC_CHECK_INTERVAL
            # print(f"  Waited {total_time_waiting} toward timeout of {SessionThreadWorker.CAMERA_RESYNC_TIMEOUT}")
            (complete_check_successful, is_complete, message) = server.get_exposure_is_complete()

        if not self._controller.thread_running():
            pass
            # Session is cancelled, we don't need to do anything except stop
        elif not complete_check_successful:
            # Error happened checking camera, return an error and the message
            success = False
        elif total_time_waiting >= SessionThreadWorker.CAMERA_RESYNC_TIMEOUT:
            # We timed out - the camera is not responding for some reason
            success = False
            message = "Timed out waiting for camera to finish"
        else:
            assert is_complete
            success = True
        return success, message

    # We're done.  If the user has requested it we'll turn of the cooler and allow the
    # CCD to warm up for a given time before disconnecting.  Return success if nothing breaks.

    def warmup_if_requested(self, server: TheSkyX, cooling_info: CameraCoolingInfo) -> bool:
        # print("warmup_if_requested")
        if cooling_info.is_regulated and cooling_info.warm_up_when_done:
            (cooling_off_success, message) = server.set_camera_cooling(False, 0)
            if cooling_off_success:
                self.console(f"Allowing camera to warm up for {cooling_info.warm_up_when_done_time} seconds", 1)
                if self.sleep_with_progress_bar(cooling_info.warm_up_when_done_time):
                    success = True
                    # We've successfully warmed the camera for the requested time
                else:
                    # Thread has been cancelled.  No message needed
                    success = False
            else:
                self.console(f"Error turning off camera cooling: {message}", 2)
                success = False
        else:
            # Camera isn't cooled or warmup not wanted.  Just succeed.
            success = True

        return success

    # When done, if requested, disconnect camera
    def disconnect_if_requested(self, server: TheSkyX, disconnect_requested: bool) -> bool:
        print(f"disconnect_if_requested({disconnect_requested})")
        success = False
        if disconnect_requested:
            (success, message) = server.disconnect_camera()
            if success:
                self.console("Camera Disconnected", 1)
            else:
                self.console(f"Error disconnecting camera: {message}", 1)
        return success
