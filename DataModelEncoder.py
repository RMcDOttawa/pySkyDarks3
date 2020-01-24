import traceback
from json import JSONEncoder

from FrameSet import FrameSet


class DataModelEncoder(JSONEncoder):

    def default(self, obj):
        # print(f"DataModelEncoder/default Encode: {obj}")

        if isinstance(obj, FrameSet):
            return obj.encode()

        print(f"DataModelEncoder: unexpected type: {obj}")
        traceback.print_exc()
        return f"Unknown DataModel Object {obj}"
