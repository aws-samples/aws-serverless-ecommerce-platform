import copy
import datetime
import json
import random
import uuid
from boto3.dynamodb.types import TypeSerializer
from botocore import stub
import pytest
from fixtures import context, lambda_module, get_order, get_product # pylint: disable=import-error
from helpers import compare_event, mock_table # pylint: disable=import-error,no-name-in-module


serialize = TypeSerializer().serialize


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "table_update",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "EVENT_BUS_NAME": "EVENT_BUS_NAME",
        "ORDERS_LIMIT": "20",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


@pytest.fixture
def order(get_order):
    return get_order()


@pytest.fixture
def ddb_record_new(order):
    return {
        "eventName": "INSERT",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1",
        "dynamodb": {
            "Keys": {
                "orderId": serialize(order["orderId"])
            },
            "NewImage": {
                "orderId": serialize(order["orderId"]),
                "status": serialize("NEW"),
                "address": serialize(order["address"])
            },
            "SequenceNumber": "123456789012345678901",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        }
    }


@pytest.fixture
def ddb_record_in_progress(order):
    return {
        "eventName": "MODIFY",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1",
        "dynamodb": {
            "Keys": {
                "orderId": serialize(order["orderId"])
            },
            "NewImage": {
                "orderId": serialize(order["orderId"]),
                "status": serialize("IN_PROGRESS"),
                "address": serialize(order["address"])
            },
            "OldImage": {
                "orderId": serialize(order["orderId"]),
                "status": serialize("NEW"),
                "address": serialize(order["address"])
            },
            "SequenceNumber": "123456789012345678901",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        }
    }


@pytest.fixture
def ddb_record_failed(order):
    return {
        "eventName": "MODIFY",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1",
        "dynamodb": {
            "Keys": {
                "orderId": serialize(order["orderId"])
            },
            "NewImage": {
                "orderId": serialize(order["orderId"]),
                "status": serialize("FAILED"),
                "address": serialize(order["address"])
            },
            "OldImage": {
                "orderId": serialize(order["orderId"]),
                "status": serialize("IN_PROGRESS"),
                "address": serialize(order["address"])
            },
            "SequenceNumber": "123456789012345678901",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        }
    }


@pytest.fixture
def ddb_record_completed(order):
    return {
        "eventName": "MODIFY",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1",
        "dynamodb": {
            "Keys": {
                "orderId": serialize(order["orderId"])
            },
            "NewImage": {
                "orderId": serialize(order["orderId"]),
                "status": serialize("COMPLETED"),
                "address": serialize(order["address"])
            },
            "OldImage": {
                "orderId": serialize(order["orderId"]),
                "status": serialize("IN_PROGRESS"),
                "address": serialize(order["address"])
            },
            "SequenceNumber": "123456789012345678901",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        }
    }


@pytest.fixture
def ddb_record_completed_removed(order):
    return {
        "eventName": "REMOVE",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1",
        "dynamodb": {
            "Keys": {
                "orderId": serialize(order["orderId"])
            },
            "OldImage": {
                "orderId": serialize(order["orderId"]),
                "status": serialize("COMPLETED"),
                "address": serialize(order["address"])
            },
            "SequenceNumber": "123456789012345678901",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        }
    }


@pytest.fixture
def ddb_record_in_progress_removed(order):
    return {
        "eventName": "REMOVE",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1",
        "dynamodb": {
            "Keys": {
                "orderId": serialize(order["orderId"])
            },
            "OldImage": {
                "orderId": serialize(order["orderId"]),
                "status": serialize("IN_PROGRESS"),
                "address": serialize(order["address"])
            },
            "SequenceNumber": "123456789012345678901",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        }
    }


def test_process_record_new(lambda_module, ddb_record_new):
    """
    Test process_record() with a new record
    """

    response = lambda_module.process_record(ddb_record_new)

    assert response is None


def test_process_record_in_progress(lambda_module, ddb_record_in_progress):
    """
    Test process_record() with an in progress record
    """

    response = lambda_module.process_record(ddb_record_in_progress)

    assert response is None


def test_process_record_failed(lambda_module, order, ddb_record_failed):
    """
    Test process_record() with a failed record
    """

    response = lambda_module.process_record(ddb_record_failed)
    
    assert response is not None
    assert response["DetailType"] == "DeliveryFailed"
    assert response["Source"] == "ecommerce.delivery"
    assert response["Resources"] == [order["orderId"]]
    assert json.loads(response["Detail"]) == {
        k: order[k] for k in ["orderId", "address"]
    }


def test_process_record_completed(lambda_module, order, ddb_record_completed):
    """
    Test process_record() with a completed record
    """

    response = lambda_module.process_record(ddb_record_completed)
    
    assert response is not None
    assert response["DetailType"] == "DeliveryCompleted"
    assert response["Source"] == "ecommerce.delivery"
    assert response["Resources"] == [order["orderId"]]
    assert json.loads(response["Detail"]) == {
        k: order[k] for k in ["orderId", "address"]
    }


def test_process_record_in_progress_removed(lambda_module, order, ddb_record_in_progress_removed):
    """
    Test process_record() with a removed in progress record
    """

    response = lambda_module.process_record(ddb_record_in_progress_removed)
    
    assert response is not None
    assert response["DetailType"] == "DeliveryFailed"
    assert response["Source"] == "ecommerce.delivery"
    assert response["Resources"] == [order["orderId"]]
    assert json.loads(response["Detail"]) == {
        k: order[k] for k in ["orderId", "address"]
    }


def test_process_record_completed_removed(lambda_module, order, ddb_record_completed_removed):
    """
    Test process_record() with a removed in progress record
    """

    response = lambda_module.process_record(ddb_record_completed_removed)
    
    assert response is None


def test_send_events(lambda_module, order):
    """
    Test send_events()
    """

    # Prepare resources
    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.delivery",
        "Resources": [order["orderId"]],
        "DetailType": "DeliveryCompleted",
        "Detail": json.dumps({
            k: order[k] for k in ["orderId", "address"]
        }),
        "EventBusName": "EVENT_BUS_NAME"
    }
    expected_event = copy.deepcopy(event)
    expected_event["Time"] = stub.ANY
    expected_params = {"Entries": [expected_event]}

    eventbridge = stub.Stubber(lambda_module.eventbridge)
    eventbridge.add_response("put_events", {}, expected_params)
    eventbridge.activate()

    # Send events
    lambda_module.send_events([event])

    # Check that events were sent
    eventbridge.assert_no_pending_responses()
    eventbridge.deactivate()


def test_handler(lambda_module, context, order,
        ddb_record_new, ddb_record_in_progress, ddb_record_failed, ddb_record_completed, ddb_record_in_progress_removed):
    """
    Test handler() with different records
    """

    # Prepare event
    event = {"Records": [
        ddb_record_new, ddb_record_in_progress, ddb_record_failed, ddb_record_completed, ddb_record_in_progress_removed
    ]}

    # Prepare stub
    expected_params = {"Entries": [
        {
            "Time": stub.ANY,
            "Source": "ecommerce.delivery",
            "Resources": [order["orderId"]],
            "DetailType": "DeliveryFailed",
            "Detail": json.dumps({
                k: order[k] for k in ["orderId", "address"]
            }),
            "EventBusName": "EVENT_BUS_NAME"
        },
        {
            "Time": stub.ANY,
            "Source": "ecommerce.delivery",
            "Resources": [order["orderId"]],
            "DetailType": "DeliveryCompleted",
            "Detail": json.dumps({
                k: order[k] for k in ["orderId", "address"]
            }),
            "EventBusName": "EVENT_BUS_NAME"
        },
        {
            "Time": stub.ANY,
            "Source": "ecommerce.delivery",
            "Resources": [order["orderId"]],
            "DetailType": "DeliveryFailed",
            "Detail": json.dumps({
                k: order[k] for k in ["orderId", "address"]
            }),
            "EventBusName": "EVENT_BUS_NAME"
        }
    ]}
    eventbridge = stub.Stubber(lambda_module.eventbridge)
    eventbridge.add_response("put_events", {}, expected_params)
    eventbridge.activate()

    lambda_module.handler(event, context)

    # Check that events were sent
    eventbridge.assert_no_pending_responses()
    eventbridge.deactivate()


def test_handler_nothing(lambda_module, context, order,
        ddb_record_new):
    """
    Test handler() with records that should not create events
    """

    # Prepare event
    event = {"Records": [
        ddb_record_new
    ]}

    # Stub
    eventbridge = stub.Stubber(lambda_module.eventbridge)
    eventbridge.activate()

    # Send request
    lambda_module.handler(event, context)

    # Check that events were sent
    eventbridge.assert_no_pending_responses()
    eventbridge.deactivate()