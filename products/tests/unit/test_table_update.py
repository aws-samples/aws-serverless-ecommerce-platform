import datetime
import decimal
import json
import uuid
import pytest
from botocore import stub
from fixtures import context, lambda_module # pylint: disable=import-error
from helpers import compare_event # pylint: disable=import-error,no-name-in-module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "table_update",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "EVENT_BUS_NAME": "EVENT_BUS_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


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


@pytest.fixture
def modify_data():
    product_old = {
        "productId": str(uuid.uuid4()),
        "name": "Old product",
        "price": 200,
        "package": {
            "width": 200,
            "length": 500,
            "height": 1000,
            "weight": 300
        }
    }

    product_new = {
        "productId": product_old["productId"],
        "name": "New product",
        "price": 201,
        "package": {
            "width": 201,
            "length": 501,
            "height": 1001,
            "weight": 301
        }
    }

    record = {
        "awsRegion": "us-east-1",
        "dynamodb": {
            "Keys": {
                "productId": {"S": product_old["productId"]}
            },
            "OldImage": {
                "productId": {"S": product_old["productId"]},
                "name": {"S": product_old["name"]},
                "price": {"N": str(product_old["price"])},
                "package": {"M": {
                    "width": {"N": str(product_old["package"]["width"])},
                    "length": {"N": str(product_old["package"]["length"])},
                    "height": {"N": str(product_old["package"]["height"])},
                    "weight": {"N": str(product_old["package"]["weight"])}
                }}
            },
            "NewImage": {
                "productId": {"S": product_new["productId"]},
                "name": {"S": product_new["name"]},
                "price": {"N": str(product_new["price"])},
                "package": {"M": {
                    "width": {"N": str(product_new["package"]["width"])},
                    "length": {"N": str(product_new["package"]["length"])},
                    "height": {"N": str(product_new["package"]["height"])},
                    "weight": {"N": str(product_new["package"]["weight"])}
                }}
            },
            "SequenceNumber": "1234567890123456789012345",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        },
        "eventID": str(uuid.uuid4()),
        "eventName": "MODIFY",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1.0"
    }
    event = {
        "Source": "ecommerce.products",
        "Resources": [product_old["productId"]],
        "DetailType": "ProductModified",
        "Detail": json.dumps({
            "old": product_old,
            "new": product_new,
            "changed": ["name", "price", "package"]
        }),
        "EventBusName": "EVENT_BUS_NAME"
    }

    return {"record": record, "event": event}


def test_send_events(lambda_module, insert_data):
    """
    Test send_events()
    """

    eventbridge = stub.Stubber(lambda_module.eventbridge)

    events = [insert_data["event"]]
    response = {}
    expected_params = {"Entries": events}

    eventbridge.add_response("put_events", response, expected_params)
    eventbridge.activate()

    lambda_module.send_events(events)

    eventbridge.assert_no_pending_responses()
    eventbridge.deactivate()


def test_handler(lambda_module, context, insert_data):
    """
    Test the Lambda function handler
    """

    # Prepare Lambda event and context
    event = {"Records": [insert_data["record"]]}

    # Stubbing boto3
    eventbridge = stub.Stubber(lambda_module.eventbridge)
    # Ignore time
    insert_data["event"]["Time"] = stub.ANY
    expected_params = {"Entries": [insert_data["event"]]}
    eventbridge.add_response("put_events", {}, expected_params)
    eventbridge.activate()

    # Send request
    lambda_module.handler(event, context)

    # Check that events were sent
    eventbridge.assert_no_pending_responses()
    eventbridge.deactivate()