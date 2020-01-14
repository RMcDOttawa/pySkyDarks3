

# The ways that the session "end date" can be specified

class EndDate:
    WHEN_DONE = "EndDate-WhenDone"  # Run until entire frame plan is done, regardless of time
    TODAY_TOMORROW = "EndDate-TodayOrTomorrow"  # Stop at specified time today, or tomorrow if today would be before start time
    GIVEN_DATE = "EndDate-GivenDate"  # Stop at given date and time

    def __init__(self):
        print("EndDate should not be instantiated")
        assert(False)