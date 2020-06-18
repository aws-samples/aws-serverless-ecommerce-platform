import copy
import datetime
import json
import time
import boto3
import pytest
from fixtures import listener, get_order, get_product # pylint: disable=import-error
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


def test_on_package_created(order, listener, table_name, event_bus_name):
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

    # Check events
    listener(
        "ecommerce.orders", 
        lambda: eventbridge.put_events(Entries=[event]),
        lambda m: (
            order["orderId"] in m["resources"] and
            m["detail-type"] == "OrderModified" and
            "status" in m["detail"]["changed"] and
            "products" not in m["detail"]["changed"] and
            m["detail"]["new"]["status"] == "PACKAGED"
        )
    )

    # Clean up
    table.delete_item(Key={"orderId": order["orderId"]})


def test_on_package_created_products(order, listener, table_name, event_bus_name):
    """
    Test OnEvents function on a PackageCreated event when there are less products
    """

    eventbridge = boto3.client("events")
    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member

    # Store order in DynamoDB table
    table.put_item(Item=order)

    package_order = copy.deepcopy(order)
    removed_product = package_order["products"].pop(0)

    # Create the event
    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.warehouse",
        "DetailType": "PackageCreated",
        "Resources": [order["orderId"]],
        "Detail": json.dumps(package_order),
        "EventBusName": event_bus_name
    }

    # Check events
    listener(
        "ecommerce.orders",
        lambda: eventbridge.put_events(Entries=[event]),
        lambda m: (
            order["orderId"] in m["resources"] and
            m["detail-type"] == "OrderModified" and
            "status" in m["detail"]["changed"] and
            "products" in m["detail"]["changed"] and
            m["detail"]["new"]["status"] == "PACKAGED"
        )
    )

    # Clean up
    table.delete_item(Key={"orderId": order["orderId"]})


def test_on_packaging_failed(order, listener, table_name, event_bus_name):
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
    
    # Check events
    listener(
        "ecommerce.orders",
        lambda: eventbridge.put_events(Entries=[event]),
        lambda m: (
            order["orderId"] in m["resources"] and
            m["detail-type"] == "OrderModified" and
            "status" in m["detail"]["changed"] and
            m["detail"]["new"]["status"] == "PACKAGING_FAILED"
        )
    )

    # Clean up
    table.delete_item(Key={"orderId": order["orderId"]})


def test_on_delivery_completed(order, listener, table_name, event_bus_name):
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

    # Check events
    listener(
        "ecommerce.orders",
        lambda: eventbridge.put_events(Entries=[event]),
        lambda m: (
            order["orderId"] in m["resources"] and
            m["detail-type"] == "OrderModified" and
            "status" in m["detail"]["changed"] and
            m["detail"]["new"]["status"] == "FULFILLED"
        )
    )

    # Clean up
    table.delete_item(Key={"orderId": order["orderId"]})


def test_on_delivery_failed(order, listener, table_name, event_bus_name):
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

    # Check events
    listener(
        "ecommerce.orders",
        lambda: eventbridge.put_events(Entries=[event]),
        lambda m: (
            order["orderId"] in m["resources"] and
            m["detail-type"] == "OrderModified" and
            "status" in m["detail"]["changed"] and
            m["detail"]["new"]["status"] == "DELIVERY_FAILED"
        )
    )

    # Clean up
    table.delete_item(Key={"orderId": order["orderId"]})