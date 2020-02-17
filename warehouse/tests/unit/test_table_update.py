import copy
import datetime
import json
import random
import uuid
from botocore import stub
import pytest
from fixtures import context, lambda_module, get_order, get_product # pylint: disable=import-error
from helpers import compare_event, mock_table # pylint: disable=import-error,no-name-in-module


METADATA_KEY = "__metadata"


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "table_update",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "METADATA_KEY": METADATA_KEY,
        "TABLE_NAME": "TABLE_NAME",
        "EVENT_BUS_NAME": "EVENT_BUS_NAME",
        "ORDERS_LIMIT": "20",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


@pytest.fixture(scope="module")
def order(get_order):
    return get_order()


@pytest.fixture
def order_products(order):
    return [
        {
            "orderId": order["orderId"],
            "productId": product["productId"],
            "quantity": product["quantity"]
        }
        for product in order["products"]
    ]


@pytest.fixture
def ddb_record_metadata_completed(order):
    return {
        "eventName": "MODIFY",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1",
        "dynamodb": {
            "Keys": {
                "orderId": {"S": order["orderId"]},
                "productId": {"S": METADATA_KEY}
            },
            "NewImage": {
                "orderId": {"S": order["orderId"]},
                "productId": {"S": METADATA_KEY},
                "status": {"S": "COMPLETED"},
                "modifiedDate": {"S": order["modifiedDate"]}
            },
            "OldImage": {
                "orderId": {"S": order["orderId"]},
                "productId": {"S": METADATA_KEY},
                "status": {"S": "IN_PROGRESS"},
                "modifiedDate": {"S": order["modifiedDate"]}
            },
            "SequenceNumber": "123456789012345678901",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        }
    }

@pytest.fixture
def event_metadata_completed(order, order_products):
    return {
        "Source": "ecommerce.warehouse",
        "DetailType": "PackageCreated",
        "Resources": [order["orderId"]],
        "EventBusName": "EVENT_BUS_NAME", 
        "Detail": json.dumps({
            "orderId": order["orderId"],
            "products": order_products
        })
    }

@pytest.fixture
def event_metadata_failed(order):
    return {
        "Source": "ecommerce.warehouse",
        "DetailType": "PackagingFailed",
        "Resources": [order["orderId"]],
        "EventBusName": "EVENT_BUS_NAME", 
        "Detail": json.dumps({
            "orderId": order["orderId"]
        })
    }


@pytest.fixture
def ddb_record_metadata_product(order):
    return {
        "eventName": "MODIFY",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1",
        "dynamodb": {
            "Keys": {
                "orderId": {"S": order["orderId"]},
                "productId": {"S": order["products"][0]["productId"]}
            },
            "NewImage": {
                "orderId": {"S": order["orderId"]},
                "productId": {"S": order["products"][0]["productId"]}
            },
            "OldImage": {
                "orderId": {"S": order["orderId"]},
                "productId": {"S": order["products"][0]["productId"]}
            },
            "SequenceNumber": "123456789012345678901",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        }
    }


@pytest.fixture
def ddb_record_metadata_removed(order):
    return {
        "eventName": "REMOVE",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1",
        "dynamodb": {
            "Keys": {
                "orderId": {"S": order["orderId"]},
                "productId": {"S": METADATA_KEY}
            },
            "OldImage": {
                "orderId": {"S": order["orderId"]},
                "productId": {"S": METADATA_KEY},
                "status": {"S": "IN_PROGRESS"},
                "modifiedDate": {"S": order["modifiedDate"]}
            },
            "SequenceNumber": "123456789012345678901",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        }
    }


def test_get_products(lambda_module, order, order_products):
    """
    Test get_products()
    """

    table = mock_table(
        lambda_module.table, "query",
        ["orderId", "productId"],
        items=order_products
    )

    response = lambda_module.get_products(order["orderId"])

    table.assert_no_pending_responses()
    table.deactivate()

    assert response == order_products


def test_parse_record_metadata_completed(lambda_module, ddb_record_metadata_completed, event_metadata_completed, order, order_products):
    """
    Test parse_record() with a metadata completed item
    """

    table = mock_table(
        lambda_module.table, "query",
        ["orderId", "productId"],
        items=order_products
    )

    response = lambda_module.parse_record(ddb_record_metadata_completed)

    table.assert_no_pending_responses()
    table.deactivate()

    assert response is not None
    compare_event(event_metadata_completed, response)


def test_parse_record_metadata_completed_empty(lambda_module, ddb_record_metadata_completed, event_metadata_failed, order, order_products):
    """
    Test parse_record() with a metadata completed item without products
    """

    table = mock_table(
        lambda_module.table, "query",
        ["orderId", "productId"]
    )

    response = lambda_module.parse_record(ddb_record_metadata_completed)

    table.assert_no_pending_responses()
    table.deactivate()

    assert response is not None
    compare_event(event_metadata_failed, response)


def test_parse_record_metadata_product(lambda_module, ddb_record_metadata_product):
    """
    Test parse_record() with a product item
    """

    response = lambda_module.parse_record(ddb_record_metadata_product)

    assert response is None


def test_parse_record_metadata_removed(lambda_module, ddb_record_metadata_removed):
    """
    Test parse_record() with a metadata removed item
    """

    response = lambda_module.parse_record(ddb_record_metadata_removed)

    assert response is None


def test_handler_metadata_completed(lambda_module, context, ddb_record_metadata_completed, ddb_record_metadata_product, ddb_record_metadata_removed, event_metadata_completed, order, order_products):
    """
    Test handler() with a metadata completed item
    """

    event_metadata_completed = copy.deepcopy(event_metadata_completed)

    table = mock_table(
        lambda_module.table, "query",
        ["orderId", "productId"],
        items=order_products
    )
    # Stubbing Event Bridge
    eventbridge = stub.Stubber(lambda_module.eventbridge)
    # Ignore time and detail
    event_metadata_completed["Time"] = stub.ANY
    event_metadata_completed["Detail"] = stub.ANY
    expected_params = {"Entries": [event_metadata_completed]}
    eventbridge.add_response("put_events", {}, expected_params)
    eventbridge.activate()

    event = {"Records": [
        ddb_record_metadata_completed,
        ddb_record_metadata_product,
        ddb_record_metadata_removed
    ]}

    lambda_module.handler(event, context)

    table.assert_no_pending_responses()
    table.deactivate()

    eventbridge.assert_no_pending_responses()
    eventbridge.deactivate()


def test_handler_metadata_completed_empty(lambda_module, context, ddb_record_metadata_completed, event_metadata_failed, order, order_products):
    """
    Test handler() with a metadata completed item but no products
    """

    event_metadata_failed = copy.deepcopy(event_metadata_failed)

    table = mock_table(
        lambda_module.table, "query",
        ["orderId", "productId"]
    )
    # Stubbing Event Bridge
    eventbridge = stub.Stubber(lambda_module.eventbridge)
    # Ignore time and detail
    event_metadata_failed["Time"] = stub.ANY
    event_metadata_failed["Detail"] = stub.ANY
    expected_params = {"Entries": [event_metadata_failed]}
    eventbridge.add_response("put_events", {}, expected_params)
    eventbridge.activate()

    event = {"Records": [
        ddb_record_metadata_completed
    ]}

    lambda_module.handler(event, context)

    table.assert_no_pending_responses()
    table.deactivate()

    eventbridge.assert_no_pending_responses()
    eventbridge.deactivate()