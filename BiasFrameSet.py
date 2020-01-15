from FrameSet import FrameSet


class BiasFrameSet(FrameSet):
    # No additional attributes for Bias Frames

    def fieldNumberAsString(self, field_number: int) -> str:
        result = "invalid"
        if field_number == 0:
            result = str(self._numberOfFrames)
        elif field_number == 1:
            result = "Bias"
        elif field_number == 2:
            result = ""
        elif field_number == 3:
            result = f"{self._binning} x {self._binning}"
        elif field_number == 4:
            result = str(self._numberComplete)
        else:
            print("fieldNumberAsString: invalid field number " + str(field_number))
        # print(f"FrameSet {self} field {field_number} returns {result}")
        return result

    def __str__(self):
        return f"BiasFrameSet<{self._numberOfFrames} BIAS {self._binning} x {self._binning}" \
               + f"({str(self._numberComplete)} complete)>"

    def encode(self):
        return {
            "_type": "BiasFrameSet",
            "_value": self.__dict__
        }

    def type_name_text(self) -> str:
        return "Bias"

    # The numeric type code for THeSkyX for this kind of image.  2=Bias, 3=Dark
    def camera_image_type_code(self) -> int:
        return 2

    @classmethod
    def decode(cls, obj):
        # print(f"BiasFrameSet/decode({obj}")
        assert (obj["_type"] == "BiasFrameSet")
        value_dict = obj['_value']
        new_number_of_frames = value_dict["_numberOfFrames"]
        new_binning = value_dict["_binning"]
        new_complete = value_dict["_numberComplete"]
        return BiasFrameSet(new_number_of_frames, new_binning, new_complete)
