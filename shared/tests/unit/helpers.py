import json
from typing import Optional
from boto3.dynamodb.types import TypeSerializer
from botocore import stub


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


def mock_table(ddb_table, action: str, key: str, item: Optional[dict]=None) -> stub.Stubber:
    """
    Mock a DynamoDB table
    """

    SUPPORTED_ACTIONS = ["get_item", "query"]

    if action not in SUPPORTED_ACTIONS:
        raise ValueError("DynamoDB action {} is not supported".format(action))

    table = stub.Stubber(ddb_table.meta.client)

    if action == "get_item":
        response = {
            "ConsumedCapacity": {}
        }
        expected_params = {
            "TableName": ddb_table.name,
            "Key": {key: stub.ANY}
        }
        if item is not None:
            response["Item"] = {k: TypeSerializer().serialize(v) for k, v in item.items()}
            expected_params["Key"] = {key: item[key]}
        table.add_response("get_item", response, expected_params)

    if action == "query":
        response = {
            "ConsumedCapacity": {}
        }
        expected_params = {
            "TableName": ddb_table.name,
            "KeyConditionExpression": stub.ANY,
            "Select": stub.ANY,
            "ExclusiveStartKey": stub.ANY
        }
        if item is not None:
            response["Items"] = [{k: TypeSerializer().serialize(v) for k, v in item.items()}]

    table.activate()

    return table