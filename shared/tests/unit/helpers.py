import json


def compare_event(a: dict, b: dict):
    """
    Compare two events

    This compares only based on the keys in 'a'. Therefore, you should put the
    test event as the first parameter.
    """
    for key, value in a.items():
        assert key in b

        if key not in b:
            continue

        if key == "Detail" and isinstance(value, str):
            value = json.loads(value)
            b[key] = json.loads(b[key])

        if isinstance(value, dict):
            compare_event(value, b[key])
        else:
            assert value == b[key]