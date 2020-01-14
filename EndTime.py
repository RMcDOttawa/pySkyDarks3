

# The ways that the session "end time" can be specified

class EndTime:
    SUNRISE = "EndTime-Sunrise"                # 4 kinds of sunrise - calculated for location
    CIVIL_DAWN = "EndTime-CivilDawn"
    NAUTICAL_DAWN = "EndTime-NauticalDawn"
    ASTRONOMICAL_DAWN = "EndTime-AstronomicalDawn"
    GIVEN_TIME = "EndTime-GivenTime"             # specified time


    def __init__(self):
        print("EndTime should not be instantiated")
        assert (False)