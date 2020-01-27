import json
import os
import boto3


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


def get_parameter(param_name: str):
    """
    Retrieve an SSM parameter
    """

    ssm = boto3.client("ssm")

    return ssm.get_parameter(
        Name=param_name.format(Environment=os.environ["ECOM_ENVIRONMENT"])
    )["Parameter"]["Value"]