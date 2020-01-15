class CameraCoolingInfo:
    def __init__(self, is_regulated: bool,
                 target_temperature: float,
                 target_tolerance: float,
                 cooling_check_interval: float,
                 max_time_to_try: float,
                 cooling_retry_count: int,
                 cooling_retry_delay: float,
                 abort_on_temperature_rise: bool,
                 abort_temperature_threshold: float,
                 warm_up_when_done: bool,
                 warm_up_when_done_time: float):
        self.is_regulated = is_regulated
        self.target_temperature = target_temperature
        self.target_tolerance = target_tolerance
        self.cooling_check_interval = cooling_check_interval
        self.max_time_to_try = max_time_to_try
        self.cooling_retry_count = cooling_retry_count
        self.cooling_retry_delay = cooling_retry_delay
        self.abort_on_temperature_rise = abort_on_temperature_rise
        self.abort_temperature_threshold = abort_temperature_threshold
        self.warm_up_when_done = warm_up_when_done
        self.warm_up_when_done_time = warm_up_when_done_time
