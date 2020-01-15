# The ways that the session "start time" can be specified


class StartTime:
    SUNSET = "StartTime-Sunset"
    CIVIL_DUSK = "StartTime-CivilDusk"
    NAUTICAL_DUSK = "StartTime-NauticalDusk"
    ASTRONOMICAL_DUSK = "StartTime-AstronomicalDusk"
    GIVEN_TIME = "StartTime-GivenTime"  # specified time

    def __init__(self):
        print("StartTime should not be instantiated")
        assert False
