class DataModelEncoder(JSONEncoder):

    def default(self, obj):
        # print(f"DataModelEncoder/default Encode: {obj}")

        if isinstance(obj, FrameSet):
            return obj.encode()

        print(f"DataModelEncoder: unexpected type: {obj}")
        return f"Unknown DataModel Object {obj}"
