import json
from typing import List, Optional, Union
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


def mock_table(
        ddb_table,
        action: str,
        keys: Union[str, List[str]],
        items: Optional[Union[dict, List[dict]]]=None,
        table_name: Optional[str]=None,
        expected_params: Optional[dict]=None,
        response: Optional[dict]=None
    ) -> stub.Stubber:
    """
    Mock a DynamoDB table
    """

    SUPPORTED_ACTIONS = [
        "delete_item", "get_item", "put_item",
        "query", "scan", "batch_write_item"
    ]

    if action not in SUPPORTED_ACTIONS:
        raise ValueError("DynamoDB action {} is not supported".format(action))

    if isinstance(ddb_table, stub.Stubber):
        table = ddb_table
    else:
        table = stub.Stubber(ddb_table.meta.client)

    if isinstance(keys, str):
        keys = [keys]

    if isinstance(items, dict):
        items = [items]

    # Key-based, one item
    if action in ["delete_item", "get_item"]:
        assert items is None or len(items) == 1
        response = response or {
            "ConsumedCapacity": {}
        }
        expected_params = expected_params or {
            "TableName": table_name or ddb_table.name,
            "Key": {key: stub.ANY for key in keys}
        }
        if items is not None and action == "get_item":
            response["Item"] = {k: TypeSerializer().serialize(v) for k, v in items[0].items()}
        if items is not None:
            expected_params["Key"] = {key: items[0][key] for key in keys}
        table.add_response(action, response, expected_params)

    # Item-based, one item
    elif action in ["put_item"]:
        assert items is None or len(items) == 1
        response = response or {
            "ConsumedCapacity": {}
        }
        expected_params = expected_params or {
            "TableName": table_name or ddb_table.name,
            "Item": stub.ANY
        }
        if items is not None:
            expected_params["Item"] = items[0]
        table.add_response(action, response, expected_params)

    # Key-based, multiple items
    elif action in ["query", "scan"]:
        response = response or {
            "ConsumedCapacity": {}
        }
        expected_params = expected_params or {
            "TableName": table_name or ddb_table.name,
            "Limit": stub.ANY
        }
        if action == "query" and "KeyConditionExpression" not in expected_params:
            expected_params["KeyConditionExpression"] = stub.ANY
        if items is not None:
            response["Items"] = [{k: TypeSerializer().serialize(v) for k, v in item.items()} for item in items]
        table.add_response(action, response, expected_params)

    # Batch operations
    elif action in ["batch_write_item"]:
        response = response or {
            "ConsumedCapacity": [{} for _ in (items or [])],
            "UnprocessedItems": {}
        }
        expected_params = expected_params or {
            "RequestItems": {
                table_name or ddb_table.name: stub.ANY
            }
        }
        if items is not None:
            expected_params["RequestItems"][table_name or ddb_table.name] = items
        table.add_response(action, response, expected_params)

    table.activate()

    return table