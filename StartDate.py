


# The ways that the session "start date" can be specified

class StartDate:
    NOW = "StartDate-Now"  # Start immediately, as soon as "begin" is clicked
    TODAY = "StartDate-Today"  # Start today at the specified time
    GIVEN_DATE = "StartDate-GivenDate"  # Start on specified future date and time

    def __init__(self):
        print("StartDate should not be instantiated")
        assert(False)