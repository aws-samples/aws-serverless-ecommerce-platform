import copy
import datetime
import decimal
import json
import uuid
import pytest
from boto3.dynamodb.types import TypeSerializer
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
def order():
    now = datetime.datetime.now()

    return {
        "orderId": str(uuid.uuid4()),
        "userId": str(uuid.uuid4()),
        "createdDate": now.isoformat(),
        "modifiedDate": now.isoformat(),
        "status": "NEW",
        "products": [{
            "productId": str(uuid.uuid4()),
            "name": "Test Product",
            "package": {
                "width": 1000,
                "length": 900,
                "height": 800,
                "weight": 700
            },
            "price": 300,
            "quantity": 4
        }],
        "address": {
            "name": "John Doe",
            "companyName": "Company Inc.",
            "streetAddress": "123 Street St",
            "postCode": "12345",
            "city": "Town",
            "state": "State",
            "country": "SE",
            "phoneNumber": "+123456789"
        },
        "deliveryPrice": 200,
        "total": 1400
    }


@pytest.fixture
def insert_data(order):
    record = {
        "awsRegion": "us-east-1",
        "dynamodb": {
            "Keys": {
                "orderId": {"S": order["orderId"]}
            },
            "NewImage": {k: TypeSerializer().serialize(v) for k, v in order.items()},
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
        "Source": "ecommerce.orders",
        "Resources": [order["orderId"]],
        "DetailType": "OrderCreated",
        "Detail": json.dumps(order),
        "EventBusName": "EVENT_BUS_NAME"
    }

    return {"record": record, "event": event}


@pytest.fixture
def remove_data(order):
    record = {
        "awsRegion": "us-east-1",
        "dynamodb": {
            "Keys": {
                "orderId": {"S": order["orderId"]}
            },
            "OldImage": {k: TypeSerializer().serialize(v) for k, v in order.items()},
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
        "Source": "ecommerce.orders",
        "Resources": [order["orderId"]],
        "DetailType": "OrderDeleted",
        "Detail": json.dumps(order),
        "EventBusName": "EVENT_BUS_NAME"
    }

    return {"record": record, "event": event}


@pytest.fixture
def modify_data(order):
    new_order = copy.deepcopy(order)
    new_order["status"] = "COMPLETED"

    record = {
        "awsRegion": "us-east-1",
        "dynamodb": {
            "Keys": {
                "orderId": {"S": order["orderId"]}
            },
            "OldImage": {k: TypeSerializer().serialize(v) for k, v in order.items()},
            "NewImage": {k: TypeSerializer().serialize(v) for k, v in new_order.items()},
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
        "Source": "ecommerce.orders",
        "Resources": [order["orderId"]],
        "DetailType": "OrderDeleted",
        "Detail": json.dumps({
            "old": order,
            "new": new_order,
            "changed": ["status"]
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