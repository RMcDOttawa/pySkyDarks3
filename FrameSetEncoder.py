from json import JSONEncoder


class FrameType(object):
    pass


class FrameSetEncoder(JSONEncoder):

    def default(self, obj):
        print(f"FrameSetEncoder/default Encode: {obj}")

        if isinstance(obj, FrameType):
            return obj.encode()

        print(f"FrameSetEncoder: unexpected type: {obj}")
        return f"Unknown FrameSet Object {obj}"
