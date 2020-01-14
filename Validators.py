class Validators:
    # Validate floating point number such as latitude, longitude
    @classmethod
    def validFloatInRange(cls, proposed_value: str, min: float, max: float) -> float:
        # print(f"validFloatInRange({proposed_value},{min},{max})")
        result: float = None
        try:
            converted: float = float(proposed_value)
            if ((converted >= min) and (converted <= max)):
                result = converted
        except ValueError:
            # Let result go back as "none", indicating error
            pass
        return result

    # Validate integer number

    @classmethod
    def validIntInRange(cls, proposed_value: str, min: int, max: int) -> int:
        # print(f"validIntInRange({proposed_value},{min},{max})")
        result: int = None
        try:
            converted: int = int(proposed_value)
            if ((converted >= min) and (converted <= max)):
                result = converted
        except ValueError:
            # Let result go back as "none", indicating error
            pass
        return result
