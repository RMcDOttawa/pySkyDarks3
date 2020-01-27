import json
from datetime import date, datetime, timedelta, time, MAXYEAR
from time import strptime, mktime
from typing import Optional

import ephem

from BiasFrameSet import BiasFrameSet
from CameraCoolingInfo import CameraCoolingInfo
from DarkFrameSet import DarkFrameSet
from DataModelEncoder import DataModelEncoder
from EndDate import EndDate
from EndTime import EndTime
from FrameSet import FrameSet
from SessionTimeInfo import SessionTimeInfo
from StartDate import StartDate
from StartTime import StartTime
from tracelog import *


class DataModel:
    # Class constants
    LATITUDE_NULL: float = -99999.0  # Indicates latitude not set
    LONGITUDE_NULL: float = -99998.0  # Indicates longitude not set
    TIMEZONE_NULL: int = -99999
    NAVAL_OBSERVATORY_HORIZON = '-0:34'
    CIVIL_TWILIGHT_HORIZON = '-6'
    NAUTICAL_TWILIGHT_HORIZON = '-12'
    ASTRONOMICAL_TWILIGHT_HORIZON = '-18'

    # On initialization, we create some dummy FrameSets for testing
    def __init__(self):
        # Location of the observatory (for calculating sun times)
        self._locationName = "EWHO"
        self._timeZone = -5
        self._latitude = 45.309645
        self._longitude = -75.886471

        # Info about when the collection run starts
        self._startDateType = StartDate.TODAY
        self._startTimeType = StartTime.CIVIL_DUSK
        now = date.today()
        self._givenStartDate = f"{now.year}-{now.month}-{now.day}"
        self._givenStartTime = "22:00"  # Arbitrary but reasonable start

        # Info about when the collection run ends
        self._endDateType = EndDate.TODAY_TOMORROW
        self._endTimeType = EndTime.CIVIL_DAWN
        tomorrow = now + timedelta(days=1)
        self._givenEndDate = f"{tomorrow.year}-{tomorrow.month}-{tomorrow.day}"
        self._givenEndTime = "03:00"  # Arbitrary but reasonable end

        # Anything extra to be done at the end of the run?
        self._disconnectWhenDone = True  # Disconnect the camera?
        self._warmUpWhenDone = True  # Let the camera warm up before disconnecting?
        self._warmUpWhenDoneSecs = 300  # How long to warm up, in seconds

        # Network address for the server running theSkyX
        self._netAddress = "localhost"
        self._portNumber = "3040"

        # We can send a "Wake On LAN" packet to the server as part of starting the run.
        # If doing this, we'll send the command in advance of the start time, so the
        # start time remains as specified
        self._sendWakeOnLanBeforeStarting = True
        self._sendWolSecondsBefore = 15 * 60  # How far in advance of start to send it
        self._wolMacAddress = "74-27-ea-5a-7c-66"  # MAC address of the computer to receive WOL
        self._wolBroadcastAddress = "255.255.255.255"  # sub-LAN containing server, with 255 at end

        # Info about the temperature management of the cooled/regulated CCD
        self._temperatureRegulated = True  # Use camera temperature regulation
        self._temperatureTarget = 0.0  # Camera target temperature
        self._temperatureWithin = 0.1  # Start when temp at target within this much
        self._temperatureSettleSeconds = 60  # Check temp every this often while cooling
        self._maxCoolingWaitTime = 30 * 60  # Try cooling for this long in one attempt
        self._temperatureFailRetryCount = 5  # If can't cool to target, wait and retry this often
        self._temperatureFailRetryDelaySeconds = 300  # Delay between cooling retries
        self._temperatureAbortOnRise = True  # Abort run if temperature rises
        self._temperatureAbortRiseLimit = 1.0  # this much

        # List of framesets that constitutes the plan.
        # A frameset is a group of 1 or more frames at a given exposure setting
        self._savedFrameSets = []  # Starts empty, contains FrameSet objects

        # When the session is running, we'll automatically save the control file after each frame
        # (if requested) so we have an up-to-date plan should a failure occur
        self._autoSaveAfterEachFrame = True

    # Getters and Setters
    # _locationName
    def get_location_name(self) -> str:
        return self._locationName

    def set_location_name(self, value: str):
        # print(f"set_location_name({value})")
        self._locationName = value

    # _timeZone
    def get_time_zone(self) -> int:
        return self._timeZone

    def set_time_zone(self, value: int):
        # print(f"set_time_zone({value})")
        self._timeZone = value

    # _latitude
    def get_latitude(self) -> float:
        return self._latitude

    def set_latitude(self, value: float):
        # print(f"set_latitude({value})")
        self._latitude = value

    # _longitude
    def get_longitude(self) -> float:
        return self._longitude

    def set_longitude(self, value: float):
        # print(f"set_longitude({value})")
        self._longitude = value

    # _startDateType
    def get_start_date_type(self) -> str:
        return self._startDateType

    def set_start_date_type(self, value: str):  # Use StartDate constants
        # print(f"set_start_date_type({value})")
        assert ((value == StartDate.NOW) or (value == StartDate.TODAY) or (value == StartDate.GIVEN_DATE))
        self._startDateType = value

    # _startTimeType
    def get_start_time_type(self) -> StartTime:
        return self._startTimeType

    def set_start_time_type(self, value: str):  # Use StartTime constants
        # print(f"set_start_time_type({value})")
        assert ((value == StartTime.SUNSET) or (value == StartTime.CIVIL_DUSK)
                or (value == StartTime.NAUTICAL_DUSK) or (value == StartTime.ASTRONOMICAL_DUSK)
                or (value == StartTime.GIVEN_TIME))
        self._startTimeType = value

    # _givenStartDate
    def get_given_start_date(self) -> str:
        return self._givenStartDate

    def set_given_start_date(self, value: str):
        # print(f"set_given_start_date({value})")
        self._givenStartDate = value

    # _givenStartTime
    def get_given_start_time(self) -> str:
        return self._givenStartTime

    def set_given_start_time(self, value: str):
        # print(f"set_given_start_time({value})")
        self._givenStartTime = value

    # _endDateType
    def get_end_date_type(self) -> str:
        return self._endDateType

    def set_end_date_type(self, value: str):
        # print(f"set_end_date_type({value})")
        assert ((value == EndDate.WHEN_DONE) or (value == EndDate.TODAY_TOMORROW) or (value == EndDate.GIVEN_DATE))
        self._endDateType = value

    # _endTimeType
    def get_end_time_type(self) -> str:
        return self._endTimeType

    # SUNRISE = "EndTime-Sunrise"                # 4 kinds of sunrise - calculated for location
    # CIVIL_DAWN = "EndTime-CivilDawn"
    # NAUTICAL_DAWN = "EndTime-NauticalDawn"
    # ASTRONOMICAL_DAWN = "EndTime-AstronomicalDawn"
    # GIVEN_TIME = "EndTime-GivenTime"             # specified time
    def set_end_time_type(self, value: str):
        # print(f"set_end_time_type({value})")
        assert ((value == EndTime.SUNRISE) or (value == EndTime.CIVIL_DAWN)
                or (value == EndTime.NAUTICAL_DAWN) or (value == EndTime.ASTRONOMICAL_DAWN)
                or (value == EndTime.GIVEN_TIME))
        self._endTimeType = value

    # _givenEndDate
    def get_given_end_date(self) -> str:
        return self._givenEndDate

    def set_given_end_date(self, value: str):
        # print(f"set_given_end_date({value})")
        self._givenEndDate = value

    # _givenEndTime
    def get_given_end_time(self) -> str:
        return self._givenEndTime

    def set_given_end_time(self, value: str):
        # print(f"set_given_end_time({value})")
        self._givenEndTime = value

    # _disconnectWhenDone
    def get_disconnect_when_done(self) -> bool:
        return self._disconnectWhenDone

    def set_disconnect_when_done(self, value: bool):
        # print(f"set_disconnect_when_done({value})")
        self._disconnectWhenDone = value

    # _warmUpWhenDone
    def get_warm_up_when_done(self) -> bool:
        return self._warmUpWhenDone

    def set_warm_up_when_done(self, value: bool):
        # print(f"set_warm_up_when_done({value})")
        self._warmUpWhenDone = value

    # _warmUpWhenDoneSecs
    def get_warm_up_when_done_secs(self) -> float:
        return self._warmUpWhenDoneSecs

    def set_warm_up_when_done_secs(self, value: float):
        # print(f"setWarmUpWhenDoneSecs({value})")
        self._warmUpWhenDoneSecs = value

    # _sendWakeOnLanBeforeStarting
    def get_send_wake_on_lan_before_starting(self) -> bool:
        return self._sendWakeOnLanBeforeStarting

    def set_send_wake_on_lan_before_starting(self, value: bool):
        # print(f"setSendWakeOnLanBeforeStarting({value})")
        self._sendWakeOnLanBeforeStarting = value

    # _sendWolSecondsBefore
    def get_send_wol_seconds_before(self) -> float:
        return self._sendWolSecondsBefore

    def set_send_wol_seconds_before(self, value: float):
        # print(f"setSendWolSecondsBefore({value})")
        self._sendWolSecondsBefore = value

    # _wolMacAddress
    def getWolMacAddress(self) -> str:
        return self._wolMacAddress

    def setWolMacAddress(self, value: str):
        # print(f"setWolMacAddress({value})")
        self._wolMacAddress = value

    # _wolBroadcastAddress
    def getWolBroadcastAddress(self) -> str:
        return self._wolBroadcastAddress

    def setWolBroadcastAddress(self, value: str):
        # print(f"setWolBroadcastAddress({value})")
        self._wolBroadcastAddress = value

    # _netAddress
    def get_net_address(self) -> str:
        return self._netAddress

    def set_net_address(self, value: str):
        # print(f"setNetAddress({value})")
        self._netAddress = value

    # _portNumber
    def get_port_number(self) -> str:
        return self._portNumber

    def set_port_number(self, value: int):
        # print(f"setPortNumber({value})")
        self._portNumber = value

    # _temperatureRegulated
    def get_temperature_regulated(self) -> bool:
        return self._temperatureRegulated

    def set_temperature_regulated(self, value: bool):
        # print(f"setTemperatureRegulated({value})")
        self._temperatureRegulated = value

    # _temperatureTarget
    def get_temperature_target(self) -> float:
        return self._temperatureTarget

    def set_temperature_target(self, value: float):
        # print(f"setTemperatureTarget({value})")
        self._temperatureTarget = value

    # _temperatureWithin
    def get_temperature_within(self) -> float:
        return self._temperatureWithin

    def set_temperature_within(self, value: float):
        # print(f"setTemperatureWithin({value})")
        self._temperatureWithin = value

    # _temperatureSettleSeconds
    def get_temperature_settle_seconds(self) -> float:
        return self._temperatureSettleSeconds

    def set_temperature_settle_seconds(self, value: float):
        # print(f"setTemperatureSettleSeconds({value})")
        self._temperatureSettleSeconds = value

    # _maxCoolingWaitTime
    def get_max_cooling_wait_time(self) -> float:
        return self._maxCoolingWaitTime

    def set_max_cooling_wait_time(self, value: float):
        # print(f"setMaxCoolingWaitTime({value})")
        self._maxCoolingWaitTime = value

    # _temperatureFailRetryCount
    def get_temperature_fail_retry_count(self) -> int:
        return self._temperatureFailRetryCount

    def set_temperature_fail_retry_count(self, value: int):
        # print(f"setTemperatureFailRetryCount({value})")
        self._temperatureFailRetryCount = value

    # _temperatureFailRetryDelaySeconds
    def get_temperature_fail_retry_delay_seconds(self) -> float:
        return self._temperatureFailRetryDelaySeconds

    def set_temperature_fail_retry_delay_seconds(self, value: float):
        # print(f"setTemperatureFailRetryDelaySeconds({value})")
        self._temperatureFailRetryDelaySeconds = value

    # _temperatureAbortOnRise
    def get_temperature_abort_on_rise(self) -> bool:
        return self._temperatureAbortOnRise

    def set_temperature_abort_on_rise(self, value: bool):
        # print(f"setTemperatureAbortOnRise({value})")
        self._temperatureAbortOnRise = value

    # _temperatureAbortRiseLimit
    def get_temperature_abort_rise_limit(self) -> float:
        return self._temperatureAbortRiseLimit

    def set_temperature_abort_rise_limit(self, value: float):
        # print(f"setTemperatureAbortRiseLimit({value})")
        self._temperatureAbortRiseLimit = value

    # _savedFrameSets
    def get_saved_frame_sets(self) -> [FrameSet]:
        return self._savedFrameSets

    def set_saved_frame_sets(self, frames_list: [FrameSet]):
        # print(f"setSavedFrameSets({framesList})")
        self._savedFrameSets = frames_list

    def get_frame_set(self, index: int) -> FrameSet:
        assert ((index >= 0) & (index < len(self._savedFrameSets)))
        return self._savedFrameSets[index]

    def set_frame_set(self, index: int, frame_set: FrameSet):
        assert ((index >= 0) & (index < len(self._savedFrameSets)))
        self._savedFrameSets[index] = frame_set

    def delete_frame_set(self, index: int):
        assert ((index >= 0) & (index < len(self._savedFrameSets)))
        del self._savedFrameSets[index]

    # _autoSaveAfterEachFrame
    def get_auto_save_after_each_frame(self) -> bool:
        return self._autoSaveAfterEachFrame

    def set_auto_save_after_each_frame(self, value: bool):
        # print(f"setAutoSaveAfterEachFrame({value})")
        self._autoSaveAfterEachFrame = value

    # Determine if we have enough information to allow the acquisition session to run
    # We need:  server address and port number, and at least one unfinished FrameSet
    @tracelog
    def session_ready_to_run(self) -> bool:
        """Determine if we have all the data we need to run an acquisition session"""
        # print("sessionReadyToRun")
        address_known = len(self._netAddress.strip()) > 0
        port_known = len(self._portNumber.strip()) > 0
        some_framesets_needed = len(self.get_incomplete_framesets()) > 0
        return address_known & port_known & some_framesets_needed

    # Get list of frameSets where # wanted > numberComplete
    @tracelog
    def get_incomplete_framesets(self) -> [FrameSet]:
        """Return a list of frame sets that still need to be acquired"""
        return list(filter(lambda fs: fs.get_number_of_frames() > fs.get_number_complete(), self._savedFrameSets))

    @tracelog
    def any_nonzero_completed_counts(self) -> bool:
        """Determine if there are any frame sets with nonzero completion counts"""
        # print("any_nonzero_completed_counts")
        for frame_set in self._savedFrameSets:
            if frame_set.get_number_complete() > 0:
                return True
        return False

    @tracelog
    def reset_completed_counts(self):
        """Set completed counts to all framesets to zero so they will be re-acquired"""
        # print("reset_completed_counts")
        for frame_set in self._savedFrameSets:
            frame_set.set_number_complete(0)

    # Add a new frameset to the end of the list
    @tracelog
    def add_frame_set(self, new_frame_set: FrameSet) -> None:
        """Append a Frame Set to the end of the frame sets list"""
        # print(f"addFrameSet entered.  Number = {len(self._savedFrameSets)}")
        self._savedFrameSets.append(new_frame_set)
        # print(f"addFrameSet exits.  Number = {len(self._savedFrameSets)}")

    # Insert a new frameset at the given position in the list
    @tracelog
    def insert_frame_set(self, new_frame_set: FrameSet, at_index: int) -> None:
        """Insert frame set into the given position in the frame sets list"""
        # print(f"insertFrameSet({at_index}) entered.  Number = {len(self._savedFrameSets)}")
        self._savedFrameSets.insert(at_index, new_frame_set)
        # print(f"insertFrameSet({at_index}) exits.  Number = {len(self._savedFrameSets)}")

    # Generate a (probably large) list of FrameSets with the given specifications
    #   - a number of bias frames at each of the given binnings
    #   - a number of dark frames at each combination of given binnings and exposures

    @staticmethod
    @tracelog
    def generate_frame_sets(num_bias_frames: int,
                            bias_binnings: [int],
                            num_dark_frames: int,
                            dark_binnings: [int],
                            dark_exposures: [float]) -> [FrameSet]:
        """Generate a list of frame sets meeting the given specifications from Bulk Add"""
        result: [FrameSet] = []

        # Bias frames
        if num_bias_frames > 0:
            for binning in bias_binnings:
                result.append(BiasFrameSet(number_of_frames=num_bias_frames, binning=binning,
                                           number_complete=0))

        # Dark frames
        if num_dark_frames > 0:
            for binning in dark_binnings:
                for exposure in dark_exposures:
                    result.append(DarkFrameSet(number_of_frames=num_dark_frames, exposure=exposure,
                                               binning=binning, number_complete=0))

        return result

    # Indicate whether we have all the information we need to calculate sunrise & set times
    # (time zone, latitude, and longitude)

    @tracelog
    def can_calculate_sunrise(self) -> bool:
        """Determine if we have all the information needed to calculate sunrise times"""
        return self.get_time_zone() != DataModel.TIMEZONE_NULL \
               and self.get_latitude() != DataModel.LATITUDE_NULL \
               and self.get_longitude() != DataModel.LONGITUDE_NULL

    # Calculate the time of sunset, return a time with no zone offset

    @tracelog
    def calc_sunset(self, start_date_type: str, given_start_date: date) -> time:
        """Calculate sunset time for the specified date"""
        # print(f"calcSunset({start_date_type}, {given_start_date})")
        # Get the date to use - today or a given date
        assert isinstance(given_start_date, date)
        (year, month, day) = self.interpret_start_date(start_date_type, given_start_date)
        # print(f"   Using date: {year},{month},{day}")
        observer = self.get_observer(year, month, day, self.NAVAL_OBSERVATORY_HORIZON)
        sun = ephem.Sun()
        sunset_utc = observer.next_setting(sun)
        sunset_local_time = ephem.localtime(sunset_utc).time()
        # print(f"Sunset UTC:{sunset_utc} local:{sunset_local_time}")

        return sunset_local_time

    # Calculate the time of sunrise
    @tracelog
    def calc_sunrise(self, end_date_type: str, given_end_date: date) -> time:
        """Calculate sunrise time for the specified date"""
        # print(f"calcSunrise({end_date_type}, {given_end_date})")
        assert isinstance(given_end_date, date)

        # Get the date to use - today or a given date
        (year, month, day) = self.interpret_end_date(end_date_type, given_end_date)

        observer = self.get_observer(year, month, day, self.NAVAL_OBSERVATORY_HORIZON)
        sun = ephem.Sun()
        sunrise_utc = observer.next_rising(sun)
        sunrise_local_time = ephem.localtime(sunrise_utc).time()

        # If sunrise has already occurred and end type is "TODAY_TOMORROW", we'll re-calculate it
        # for tomorrow.
        today: datetime = datetime.now()
        current_time = today.time()
        if (current_time > sunrise_local_time) and (end_date_type == EndDate.TODAY_TOMORROW):
            # print(f"   Sunrise {sunrise_local_time} has already occurred, switching to tomorrow")
            tomorrow = today + timedelta(days=1)
            # print(f"   Tomorrow: {tomorrow}")
            sunrise_local_time = self.calc_sunrise(EndDate.GIVEN_DATE, tomorrow.date())
            # print(f"   Adjusted sunrise: {sunrise_local_time}")
        return sunrise_local_time


    @tracelog
    def interpret_end_date(self, end_date_type: str, given_end_date: date) -> (int, int, int):
        today: datetime = datetime.now()
        if end_date_type == EndDate.GIVEN_DATE:
            year = given_end_date.year
            month = given_end_date.month
            day = given_end_date.day
        else:
            year = today.year
            month = today.month
            day = today.day
        return year, month, day

    # Calculate the various sun-based times, based on current location
    @tracelog
    def calc_civil_dusk(self, start_date_type: str, given_start_date: date) -> time:
        """Calculate the time of Civil Dusk on the given date"""
        assert isinstance(given_start_date, date)

        (year, month, day) = self.interpret_start_date(start_date_type, given_start_date)

        observer = self.get_observer(year, month, day, self.CIVIL_TWILIGHT_HORIZON)
        sun = ephem.Sun()
        dusk_utc = observer.next_setting(sun, use_center=True)
        dusk_local_time = ephem.localtime(dusk_utc).time()

        return dusk_local_time

    @tracelog
    def interpret_start_date(self, start_date_type: str, given_start_date: date) -> (int, int, int):
        if start_date_type == StartDate.GIVEN_DATE:
            year = given_start_date.year
            month = given_start_date.month
            day = given_start_date.day
        else:
            now = datetime.now()
            year = now.year
            month = now.month
            day = now.day
        return year, month, day

    @tracelog
    def calc_nautical_dusk(self, start_date_type: str, given_start_date: date) -> time:
        """Calculate the time of Nautical Dusk on the given date"""
        assert isinstance(given_start_date, date)
        (year, month, day) = self.interpret_start_date(start_date_type, given_start_date)

        observer = self.get_observer(year, month, day, self.NAUTICAL_TWILIGHT_HORIZON)
        sun = ephem.Sun()
        dusk_utc = observer.next_setting(sun, use_center=True)
        dusk_local_time = ephem.localtime(dusk_utc).time()

        return dusk_local_time

    @tracelog
    def calc_astronomical_dusk(self, start_date_type: str, given_start_date: date) -> time:
        """Calculate the time of Astronomical Dusk on the given date"""
        assert isinstance(given_start_date, date)
        (year, month, day) = self.interpret_start_date(start_date_type, given_start_date)

        observer = self.get_observer(year, month, day, self.ASTRONOMICAL_TWILIGHT_HORIZON)
        sun = ephem.Sun()
        dusk_utc = observer.next_setting(sun, use_center=True)
        dusk_local_time = ephem.localtime(dusk_utc).time()

        return dusk_local_time

    @tracelog
    def calc_civil_dawn(self, end_date_type: str, given_end_date: date) -> time:
        """Calculate the time of Civil Dawn on the given date"""
        # print(f"calcCivilDawn({end_date_type}, {given_end_date})")
        assert isinstance(given_end_date, date)
        # Get the date to use - today or a given date
        (year, month, day) = self.interpret_end_date(end_date_type, given_end_date)

        observer = self.get_observer(year, month, day, self.CIVIL_TWILIGHT_HORIZON)
        sun = ephem.Sun()
        sunrise_utc = observer.next_rising(sun)
        sunrise_local_time = ephem.localtime(sunrise_utc).time()

        # If dawn has already occurred and end type is "TODAY_TOMORROW", we'll re-calculate it
        # for tomorrow.
        today: datetime = datetime.now()
        current_time = today.time()
        if (current_time > sunrise_local_time) and (end_date_type == EndDate.TODAY_TOMORROW):
            # print(f"   Civil dawn {sunrise_local_time} has already occurred, switching to tomorrow")
            tomorrow = today + timedelta(days=1)
            # print(f"   Tomorrow: {tomorrow}")
            sunrise_local_time = self.calc_civil_dawn(EndDate.GIVEN_DATE, tomorrow.date())
            # print(f"   Adjusted Civil dawn: {sunrise_local_time}")
        return sunrise_local_time

    @tracelog
    def calc_nautical_dawn(self, end_date_type: str, given_end_date: date) -> time:
        """Calculate the time of Nautical Dawn on the given date"""
        # print(f"calcNauticalDawn({start_date_type}, {given_start_date})")
        assert isinstance(given_end_date, date)
        # Get the date to use - today or a given date
        (year, month, day) = self.interpret_end_date(end_date_type, given_end_date)

        observer = self.get_observer(year, month, day, self.NAUTICAL_TWILIGHT_HORIZON)
        sun = ephem.Sun()
        sunrise_utc = observer.next_rising(sun)
        sunrise_local_time = ephem.localtime(sunrise_utc).time()

        # If dawn has already occurred and end type is "TODAY_TOMORROW", we'll re-calculate it
        # for tomorrow.
        today: datetime = datetime.now()
        current_time = today.time()
        if (current_time > sunrise_local_time) and (end_date_type == EndDate.TODAY_TOMORROW):
            # print(f"   Nautical dawn {sunrise_local_time} has already occurred, switching to tomorrow")
            tomorrow = today + timedelta(days=1)
            # print(f"   Tomorrow: {tomorrow}")
            sunrise_local_time = self.calc_nautical_dawn(EndDate.GIVEN_DATE, tomorrow.date())
            # print(f"   Adjusted Nautical dawn: {sunrise_local_time}")
        return sunrise_local_time

    @tracelog
    def calc_astronomical_dawn(self, end_date_type: str, given_end_date: date) -> time:
        """Calculate the time of Astronomical Dawn on the given date"""
        # print(f"calcAstronomicalDawn({start_date_type}, {given_start_date})")
        assert isinstance(given_end_date, date)
        # Get the date to use - today or a given date
        (year, month, day) = self.interpret_end_date(end_date_type, given_end_date)

        observer = self.get_observer(year, month, day, self.ASTRONOMICAL_TWILIGHT_HORIZON)
        sun = ephem.Sun()
        sunrise_utc = observer.next_rising(sun)
        sunrise_local_time = ephem.localtime(sunrise_utc).time()

        # If dawn has already occurred and end type is "TODAY_TOMORROW", we'll re-calculate it
        # for tomorrow.
        today: datetime = datetime.now()
        current_time = today.time()
        if (current_time > sunrise_local_time) and (end_date_type == EndDate.TODAY_TOMORROW):
            # print(f"   Astronomical dawn {sunrise_local_time} has already occurred, switching to tomorrow")
            tomorrow = today + timedelta(days=1)
            # print(f"   Tomorrow: {tomorrow}")
            sunrise_local_time = self.calc_astronomical_dawn(EndDate.GIVEN_DATE, tomorrow.date())
            # print(f"   Adjusted Astronomical dawn: {sunrise_local_time}")
        return sunrise_local_time

    # Produce a JSON serialization of this data model for writing to a file
    @tracelog
    def serialize_to_json(self) -> str:
        """Convert the data modle to a json-encoded string"""
        # print("serializeToJson")
        # self.clear_ephemeris()
        serialized = json.dumps(self.__dict__, cls=DataModelEncoder, indent=4)
        return serialized

    # Update all the local fields in this model from the given loaded JSON dictionary
    @tracelog
    def update_from_loaded_json(self, new_values: {}):
        """Set data model fields from given json-encoded dict"""
        # print(f"DataModel/updateFromLoadedJson: {new_values}")
        # Do the update manually so we can test for missing and extra key/value pairs
        for k, v in self.__dict__.items():
            # print(f"  Checking key {k}")
            # print(f"     Old value {v}")
            if k in new_values:
                # Update this attribute in the data model from the saved file
                new_value = new_values[k]
                self.__dict__[k] = new_value
                del new_values[k]
            else:
                # The data model contains an attribute not in the saved file
                print(f"Data model key {k} missing from saved file, left unchanged")

        # Anything left in the new values hasn't been handled
        for k, v in new_values.items():
            # The saved file contains an attribute not in the data model
            print(f"Key {k} in saved file is not part of data model, ignored.")

    # Copy all the attribute values from the given model into self
    @tracelog
    def load_from_model(self, source_model):
        # print("loadFromModel")
        self.__dict__.update(source_model.__dict__)
        return

    # Get and return everything you'd need to know about when to start and end the session
    #  Start Time
    #      If "now", record that as boolean flag.
    #      Otherwise, use the specified date and time.
    #      If "today' and the time has passed, treat this as "now"
    #  Stop Time
    #      If "when done", record that as boolean flag.
    #      Otherwise, use specified date and time.
    #      If date & time is  earlier than the start date & time, advance one day

    @tracelog
    def get_session_time_info(self) -> SessionTimeInfo:
        """Create complete description of session start/end parameters"""
        # First, start time
        today: date = date.today()
        right_now: time = datetime.now().time()
        _start_date_type = self.get_start_date_type()
        if _start_date_type == StartDate.NOW:
            start_now = True
            start_date = today
            start_time = right_now
        elif _start_date_type == StartDate.TODAY:
            start_now = False
            start_date = today
            start_time = self.appropriate_start_time()
        else:
            assert (_start_date_type == StartDate.GIVEN_DATE)
            start_now = False
            start_date = self.parse_date(self.get_given_start_date())
            start_time = self.appropriate_start_time()
        if not start_now:
            _current_time_localized = datetime.now().time()
            if (start_date == today) and (start_time < _current_time_localized):
                print("Missed start time, start now")
                # We've missed the start time, just start now
                start_now = True
                start_date = today
                start_time = right_now
        start_date_time = datetime.combine(start_date, start_time)

        # End date & time?

        _end_date_type = self.get_end_date_type()
        if _end_date_type == EndDate.WHEN_DONE:
            stop_when_done = True
            end_date = date(MAXYEAR, 12, 31)
            end_time = time(23, 59, 59)
        elif _end_date_type == EndDate.TODAY_TOMORROW:
            stop_when_done = False
            end_time = self.appropriate_end_time()

            if (end_time is not None) and (end_time > start_time):
                end_date = today
            else:
                # The stated time (often morning) has already passed, so we
                # assume they meant *tomorrow* morning
                end_date = today + timedelta(days=1)
        else:
            assert (_end_date_type == EndDate.GIVEN_DATE)
            stop_when_done = False
            end_date = DataModel.parse_date(self.get_given_end_date())
            end_time = self.appropriate_end_time()
        end_date_time: datetime = datetime.combine(end_date, end_time)

        return SessionTimeInfo(start_now, start_date_time, stop_when_done, end_date_time)

    @classmethod
    @tracelog
    def parse_date(cls, string: str) -> date:
        """Convert date string in yyyy-mm-dd format to python date"""
        parts = string.split('-')
        return date(int(parts[0]), int(parts[1]), int(parts[2]))

    # Returns a time object without timezone offset
    @tracelog
    def appropriate_start_time(self) -> Optional[time]:
        """Get the appropriate start time given the various time and sunset settings."""
        # print("appropriate_start_time entered")
        result: Optional[time] = None
        start_date: date = date.today()
        _start_date_type = self.get_start_date_type()
        _given_start_date_string: str = self.get_given_start_date()
        if _start_date_type == StartDate.GIVEN_DATE:
            start_date = DataModel.parse_date(_given_start_date_string)
            # print("   Using given start date")
        _start_time_type = self.get_start_time_type()
        if _start_time_type == StartTime.SUNSET:
            if (self.get_latitude() != DataModel.LATITUDE_NULL) and (self.get_longitude() != DataModel.LONGITUDE_NULL):
                result = self.calc_sunset(_start_date_type, start_date)
                # print("   Using sunset")
        elif _start_time_type == StartTime.CIVIL_DUSK:
            if (self.get_latitude() != DataModel.LATITUDE_NULL) and (self.get_longitude() != DataModel.LONGITUDE_NULL):
                result = self.calc_civil_dusk(_start_date_type, start_date)
                # print("   Using civil dusk")
        elif _start_time_type == StartTime.NAUTICAL_DUSK:
            if (self.get_latitude() != DataModel.LATITUDE_NULL) and (self.get_longitude() != DataModel.LONGITUDE_NULL):
                result = self.calc_nautical_dusk(_start_date_type, start_date)
                # print("   Using nautical dusk")
        elif _start_time_type == StartTime.ASTRONOMICAL_DUSK:
            if (self.get_latitude() != DataModel.LATITUDE_NULL) and (self.get_longitude() != DataModel.LONGITUDE_NULL):
                result = self.calc_astronomical_dusk(_start_date_type, start_date)
                # print("   Using astronomical dusk")
        else:
            assert (_start_time_type == StartTime.GIVEN_TIME)
            struct_time = strptime(self.get_given_start_time(), "%H:%M")
            result = datetime.fromtimestamp(mktime(struct_time)).time()
            # print("   using given start time")
        # print(f"get_appropriate_start_time exits: {result}")
        return result

    # Returns a time object without timezone offset
    @tracelog
    def appropriate_end_time(self) -> Optional[time]:
        """Get the appropriate end time given the various time and sunset settings."""
        # print("appropriate_end_time entered")
        result: Optional[time] = None
        end_date = date.today()
        end_date_type: str = self.get_end_date_type()
        given_end_date_string: str = self.get_given_end_date()
        if end_date_type == EndDate.GIVEN_DATE:
            end_date = DataModel.parse_date(given_end_date_string)
        end_time_type: str = self.get_end_time_type()
        if end_time_type == EndTime.SUNRISE:
            if (self.get_latitude() != DataModel.LATITUDE_NULL) and (self.get_longitude() != DataModel.LONGITUDE_NULL):
                result = self.calc_sunrise(end_date_type, end_date)
                # print("  Using sunrise")
        elif end_time_type == EndTime.CIVIL_DAWN:
            if (self.get_latitude() != DataModel.LATITUDE_NULL) and (self.get_longitude() != DataModel.LONGITUDE_NULL):
                result = self.calc_civil_dawn(end_date_type, end_date)
                # print("  Using civil dawn")
        elif end_time_type == EndTime.NAUTICAL_DAWN:
            if (self.get_latitude() != DataModel.LATITUDE_NULL) and (self.get_longitude() != DataModel.LONGITUDE_NULL):
                result = self.calc_nautical_dawn(end_date_type, end_date)
                # print("  Using nautical dawn")
        elif end_time_type == EndTime.ASTRONOMICAL_DAWN:
            if (self.get_latitude() != DataModel.LATITUDE_NULL) and (self.get_longitude() != DataModel.LONGITUDE_NULL):
                result = self.calc_astronomical_dawn(end_date_type, end_date)
                # print("  Using astronomical dawn")
        else:
            assert (end_time_type == EndTime.GIVEN_TIME)
            struct_time = strptime(self.get_given_end_time(), "%H:%M")
            result = datetime.fromtimestamp(mktime(struct_time)).time()
        # print(f"appropriate_end_time exits: {result}")
        return result

    @tracelog
    def get_session_temperature_info(self) -> CameraCoolingInfo:
        """Get complete description of temperature data for the session"""
        return CameraCoolingInfo(self._temperatureRegulated, self._temperatureTarget,
                                 self._temperatureWithin, self._temperatureSettleSeconds,
                                 self._maxCoolingWaitTime, self._temperatureFailRetryCount,
                                 self._temperatureFailRetryDelaySeconds, self._temperatureAbortOnRise,
                                 self._temperatureAbortRiseLimit,
                                 self._warmUpWhenDone, self._warmUpWhenDoneSecs)

    def get_observer(self, year: int, month: int, day: int, horizon: str) -> ephem.Observer:
        result = ephem.Observer()
        result.lat = str(self.get_latitude())
        result.lon = str(self.get_longitude())
        result.date = datetime(year, month, day)
        result.elevation = 3  # meters
        result.pressure = 0  # millibar
        result.horizon = horizon
        return result
