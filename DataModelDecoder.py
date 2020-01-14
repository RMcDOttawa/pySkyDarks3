
class DataModelDecoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        # print(f"DataModelDecoder/object_hook({obj}")

        if '_type' not in obj:
            return obj
        custom_type_name = obj['_type']
        result = None
        if custom_type_name == "BiasFrameSet":
            result = BiasFrameSet.decode(obj)
        elif custom_type_name == "DarkFrameSet":
            result = DarkFrameSet.decode(obj)
        else:
            print(f"** Unknown custom object type in decoder: {custom_type_name}")
            assert(False)
        return result
