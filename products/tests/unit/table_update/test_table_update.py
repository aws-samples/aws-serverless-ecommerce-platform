import copy
import importlib
import json
import os
import sys
import uuid
import pytest


FUNCTION_DIR = "table_update"
MODULE_NAME = "main"
ENVIRON = {
    "ENVIRONMENT": "test",
    "EVENT_BUS_NAME": "EVENT_BUS_NAME",
    "POWERTOOLS_TRACE_DISABLED": "true"
}


@pytest.fixture(scope="module")
def lambda_module():
    """
    Main module of the Lambda function

    This also load environment variables and the path to the Lambda function
    prior to loading the module itself.
    """

    # Inject environment variables
    backup_environ = {}
    for key, value in ENVIRON.items():
        if key in os.environ:
            backup_environ[key] = os.environ[key]
        os.environ[key] = value

    # Add path for Lambda function
    sys.path.insert(0, os.path.join(os.environ["BUILD_DIR"], "src", FUNCTION_DIR))

    # Save the list of previously loaded modules
    prev_modules = list(sys.modules.keys())

    # Return the function module
    module = importlib.import_module(MODULE_NAME)
    yield module

    # Delete newly loaded modules
    new_keys = list(sys.modules.keys())
    for key in new_keys:
        if key not in prev_modules:
            del sys.modules[key]

    # Delete function module
    del module

    # Remove the Lambda function from path
    sys.path.pop(0)

    # Restore environment variables
    for key in ENVIRON.keys():
        if key in backup_environ:
            os.environ[key] = backup_environ[key]
        else:
            del os.environ[key]


@pytest.fixture
def insert_data():
    product = {
        "productId": str(uuid.uuid4()),
        "name": "Insert product",
        "price": 200,
        "package": {
            "width": 200,
            "length": 500,
            "height": 1000,
            "weight": 300
        }
    }

    record = {
        "awsRegion": "us-east-1",
        "dynamodb": {
            "Keys": {
                "productId": {"S": product["productId"]}
            },
            "NewImage": {
                "productId": {"S": product["productId"]},
                "name": {"S": product["name"]},
                "price": {"N": str(product["price"])},
                "package": {"M": {
                    "width": {"N": str(product["package"]["width"])},
                    "length": {"N": str(product["package"]["length"])},
                    "height": {"N": str(product["package"]["height"])},
                    "weight": {"N": str(product["package"]["weight"])}
                }}
            },
            "SequenceNumber": "1234567890123456789012345",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        },
        "eventID": str(uuid.uuid4()),
        "eventName": "INSERT",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1.0"
    }
    event = {
        "Source": "ecommerce.products",
        "Resources": [product["productId"]],
        "DetailType": "ProductCreated",
        "Detail": json.dumps(product),
        "EventBusName": "EVENT_BUS_NAME"
    }

    return {"record": record, "event": event}


@pytest.fixture
def remove_data():
    product = {
        "productId": str(uuid.uuid4()),
        "name": "Delete product",
        "price": 200,
        "package": {
            "width": 200,
            "length": 500,
            "height": 1000,
            "weight": 300
        }
    }

    record = {
        "awsRegion": "us-east-1",
        "dynamodb": {
            "Keys": {
                "productId": {"S": product["productId"]}
            },
            "OldImage": {
                "productId": {"S": product["productId"]},
                "name": {"S": product["name"]},
                "price": {"N": str(product["price"])},
                "package": {"M": {
                    "width": {"N": str(product["package"]["width"])},
                    "length": {"N": str(product["package"]["length"])},
                    "height": {"N": str(product["package"]["height"])},
                    "weight": {"N": str(product["package"]["weight"])}
                }}
            },
            "SequenceNumber": "1234567890123456789012345",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        },
        "eventID": str(uuid.uuid4()),
        "eventName": "REMOVE",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1.0"
    }
    event = {
        "Source": "ecommerce.products",
        "Resources": [product["productId"]],
        "DetailType": "ProductDeleted",
        "Detail": json.dumps(product),
        "EventBusName": "EVENT_BUS_NAME"
    }

    return {"record": record, "event": event}


def test_process_record_insert(lambda_module, insert_data):
    """
    Test process_record() against an INSERT event
    """

    retval = lambda_module.process_record(insert_data["record"])

    def _compare_dict(a: dict, b: dict):
        for key, value in a.items():
            assert key in b

            if key not in b:
                continue

            if key == "Detail" and isinstance(value, str):
                value = json.loads(value)
                b[key] = json.loads(b[key])

            if isinstance(value, dict):
                _compare_dict(value, b[key])
            else:
                assert value == b[key]

    _compare_dict(insert_data["event"], retval)


def test_process_record_remove(lambda_module, remove_data):
    """
    Test process_record() against a REMOVE event
    """

    retval = lambda_module.process_record(remove_data["record"])

    def _compare_dict(a: dict, b: dict):
        for key, value in a.items():
            assert key in b

            if key not in b:
                continue

            if key == "Detail" and isinstance(value, str):
                value = json.loads(value)
                b[key] = json.loads(b[key])

            if isinstance(value, dict):
                _compare_dict(value, b[key])
            else:
                assert value == b[key]

    _compare_dict(remove_data["event"], retval)