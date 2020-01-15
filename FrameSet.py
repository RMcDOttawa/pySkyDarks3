from abc import ABC, abstractmethod


class FrameSet(ABC):
    # Attributes common to all subclasses
    # _numberOfFrames = 16
    # _binning = 1
    # _numberComplete = 0

    NUMBER_OF_DISPLAY_FIELDS = 5

    # Getters and Setters
    def get_number_of_frames(self): return self._numberOfFrames

    def set_number_of_frames(self, value):  self._numberOfFrames = value

    def get_binning(self): return self._binning

    def set_binning(self, value):  self._binning = value

    def get_number_complete(self): return self._numberComplete

    def set_number_complete(self, value):  self._numberComplete = value

    # Creators

    def __init__(self, number_of_frames: int = 16,
                 binning: int = 1,
                 number_complete: int = 0):
        self._numberOfFrames = number_of_frames
        self._binning = binning
        self._numberComplete = number_complete

    @abstractmethod
    def encode(self):
        pass

    @abstractmethod
    def decode(cls, obj):
        pass

    @abstractmethod
    def fieldNumberAsString(self, field_number: int) -> str:
        pass

    @abstractmethod
    def type_name_text(self) -> str:
        pass

    # The numeric type code for THeSkyX for this kind of image.  2=Bias, 3=Dark
    @abstractmethod
    def camera_image_type_code(self) -> int:
        pass
