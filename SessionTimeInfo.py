# Everything you'd want to know about when to start and stop a session
from datetime import datetime


class SessionTimeInfo:

    def __init__(self, start_now: bool,
                 start_date_time: datetime,
                 end_when_done: bool,
                 end_date_time: datetime):
        # print(f"SessionTimeInfo({start_now},{start_date_time},{end_when_done},{end_date_time})")
        #  When to start the session
        self._start_now: bool = start_now
        self._start_date_time: datetime = start_date_time

        # When to stop the session
        self._end_when_done: bool = end_when_done
        self._end_date_time: datetime = end_date_time

    # Getters and Setters
    def get_start_now(self) -> bool:
        return self._start_now

    def set_start_now(self, sn: bool):
        self._start_now = sn

    def get_start_date_time(self) -> datetime:
        return self._start_date_time

    def set_start_date_time(self, dt: datetime):
        self._start_date_time = dt

    def get_end_when_done(self) -> bool:
        return self._end_when_done

    def set_end_when_done(self, ewd: bool):
        self._end_when_done = ewd

    def get_end_date_time(self) -> datetime:
        return self._end_date_time

    def set_end_date_time(self, edt: datetime):
        self._end_date_time = edt

    def __str__(self):

        # Start part
        if self.get_start_now():
            start_part = "Now"
        else:
            start_part = str(self.get_start_date_time())

        # End part
        if self.get_end_when_done():
            end_part = "When Done"
        else:
            end_part = str(self.get_end_date_time())

        return "Start " + start_part + ", end " + end_part
