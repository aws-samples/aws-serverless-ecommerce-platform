import datetime
import json
import time
import boto3
import pytest
from fixtures import get_order, get_product # pylint: disable=import-error
from helpers import get_parameter # pylint: disable=import-error,no-name-in-module


@pytest.fixture
def table_name():
    """
    DynamoDB table name
    """

    return get_parameter("/ecommerce/{Environment}/orders/table/name")


@pytest.fixture
def event_bus_name():
    """
    Event Bus name
    """

    return get_parameter("/ecommerce/{Environment}/platform/event-bus/name")


@pytest.fixture(scope="function")
def order(get_order):
    return get_order()


def test_on_package_created(order, table_name, event_bus_name):
    """
    Test OnEvents function on a PackageCreated event
    """

    eventbridge = boto3.client("events")
    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member

    # Store order in DynamoDB table
    table.put_item(Item=order)

    # Create the event
    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.warehouse",
        "DetailType": "PackageCreated",
        "Resources": [order["orderId"]],
        "Detail": json.dumps(order),
        "EventBusName": event_bus_name
    }
    eventbridge.put_events(Entries=[event])

    # Wait
    time.sleep(5)

    # Check the DynamoDB table
    response = table.get_item(Key={"orderId": order["orderId"]})
    assert "Item" in response
    assert "status" in response["Item"]
    assert response["Item"]["status"] == "PACKAGED"

    # Clean up
    table.delete_item(Key={"orderId": order["orderId"]})


def test_on_packaging_failed(order, table_name, event_bus_name):
    """
    Test OnEvents function on a PackagingFailed event
    """

    eventbridge = boto3.client("events")
    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member

    # Store order in DynamoDB table
    table.put_item(Item=order)

    # Create the event
    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.warehouse",
        "DetailType": "PackagingFailed",
        "Resources": [order["orderId"]],
        "Detail": json.dumps(order),
        "EventBusName": event_bus_name
    }
    eventbridge.put_events(Entries=[event])

    # Wait
    time.sleep(5)

    # Check the DynamoDB table
    response = table.get_item(Key={"orderId": order["orderId"]})
    assert "Item" in response
    assert "status" in response["Item"]
    assert response["Item"]["status"] == "PACKAGING_FAILED"

    # Clean up
    table.delete_item(Key={"orderId": order["orderId"]})


def test_on_delivery_completed(order, table_name, event_bus_name):
    """
    Test OnEvents function on a DeliveryCompleted event
    """

    eventbridge = boto3.client("events")
    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member

    # Store order in DynamoDB table
    table.put_item(Item=order)

    # Create the event
    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.delivery",
        "DetailType": "DeliveryCompleted",
        "Resources": [order["orderId"]],
        "Detail": json.dumps(order),
        "EventBusName": event_bus_name
    }
    eventbridge.put_events(Entries=[event])

    # Wait
    time.sleep(5)

    # Check the DynamoDB table
    response = table.get_item(Key={"orderId": order["orderId"]})
    assert "Item" in response
    assert "status" in response["Item"]
    assert response["Item"]["status"] == "FULFILLED"

    # Clean up
    table.delete_item(Key={"orderId": order["orderId"]})


def test_on_delivery_failed(order, table_name, event_bus_name):
    """
    Test OnEvents function on a DeliveryFailed event
    """

    eventbridge = boto3.client("events")
    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member

    # Store order in DynamoDB table
    table.put_item(Item=order)

    # Create the event
    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.delivery",
        "DetailType": "DeliveryFailed",
        "Resources": [order["orderId"]],
        "Detail": json.dumps(order),
        "EventBusName": event_bus_name
    }
    eventbridge.put_events(Entries=[event])

    # Wait
    time.sleep(5)

    # Check the DynamoDB table
    response = table.get_item(Key={"orderId": order["orderId"]})
    assert "Item" in response
    assert "status" in response["Item"]
    assert response["Item"]["status"] == "DELIVERY_FAILED"

    # Clean up
    table.delete_item(Key={"orderId": order["orderId"]})