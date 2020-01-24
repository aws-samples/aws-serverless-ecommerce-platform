import json


def compare_dict(a: dict, b: dict):
    """
    Compare two dicts

    This compares only based on the keys in 'a'. Therefore, you should put the
    test event as the first parameter.
    """

    for key, value in a.items():
        assert key in b

        if key not in b:
            continue

        if isinstance(value, dict):
            compare_dict(value, b[key])
        else:
            assert value == b[key]


def compare_event(a: dict, b: dict):
    """
    Compare two events

    Compared to `compare_dict`, this transforms "Detail" keys from JSON
    serialized string into dict.

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