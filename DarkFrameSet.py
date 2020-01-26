from FrameSet import FrameSet
from tracelog import *


class DarkFrameSet(FrameSet):
    # Additional Attributes for Dark Frames
    # _exposure

    def __init__(self, number_of_frames: int = 16,
                 exposure: float = 300,
                 binning: int = 1,
                 number_complete: int = 0):
        FrameSet.__init__(self, number_of_frames=number_of_frames, binning=binning, number_complete=number_complete)
        self._exposure_seconds: float = exposure

    def get_exposure_seconds(self): return self._exposure_seconds
    def set_exposure_seconds(self, value):  self._exposure_seconds = value

    #tracelog
    def fieldNumberAsString(self, field_number: int) -> str:
        """Translate column number of frame table to a string, for dark frames"""
        result = "invalid"
        if field_number == 0:
            result = str(self._numberOfFrames)
        elif field_number == 1:
            result = "Dark"
        elif field_number == 2:
            result = str(self._exposure_seconds)
        elif field_number == 3:
            result = f"{self._binning} x {self._binning}"
        elif field_number == 4:
            result = str(self._numberComplete)
        else:
            print("fieldNumberAsString: invalid field number " + str(field_number))
        # print(f"DarkFrameSet {self} field {field_number} returns {result}")
        return result

    def __str__(self):
        return f"DarkFrameSet<{self._numberOfFrames} DARK {str(self._exposure_seconds)} secs" \
                + f"{self._binning} x {self._binning} ({str(self._numberComplete)} complete)>"

    @tracelog
    def encode(self):
        """JSON-encode this Dark Frame set"""
        return {
            "_type": "DarkFrameSet",
            "_value": self.__dict__
        }

    def type_name_text(self) -> str:
        """Return printable name for this kind of frame"""
        return "Dark"

    # The numeric type code for THeSkyX for this kind of image.  2=Bias, 3=Dark
    @tracelog
    def camera_image_type_code(self) -> int:
        """Return magic type number that TheSkyX uses for dark frames"""
        return 3

    @classmethod
    def decode(cls, obj):
        """Make a DarkFrameSet from json-encoded dict object"""
        # print(f"DarkFrameSet/decode({obj}")
        assert (obj["_type"] == "DarkFrameSet")
        value_dict = obj['_value']
        new_number_of_frames = value_dict["_numberOfFrames"]
        new_binning = value_dict["_binning"]
        new_complete = value_dict["_numberComplete"]
        new_exposure = value_dict["_exposure_seconds"]
        return DarkFrameSet(new_number_of_frames, new_exposure, new_binning, new_complete)
