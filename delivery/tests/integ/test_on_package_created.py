import json
import time
import datetime
import boto3
from boto3.dynamodb.conditions import Key
import pytest
from fixtures import get_order, get_product # pylint: disable=import-error
from helpers import get_parameter # pylint: disable=import-error,no-name-in-module


@pytest.fixture(scope="module")
def delivery_table_name():
    return get_parameter("/ecommerce/{Environment}/delivery/table/name")


@pytest.fixture(scope="module")
def orders_table_name():
    return get_parameter("/ecommerce/{Environment}/orders/table/name")


@pytest.fixture(scope="module")
def event_bus_name():
    """
    Event Bus name
    """

    return get_parameter("/ecommerce/{Environment}/platform/event-bus/name")


@pytest.fixture
def order(get_order):
    return get_order()


@pytest.fixture
def package_created_event(order, event_bus_name):
    """
    Event indicating a package was created for delivery
    """

    return  {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.warehouse",
        "Resources": [order["orderId"]],
        "DetailType": "PackageCreated",
        "Detail": json.dumps(order),
        "EventBusName": event_bus_name
    }


def test_on_package_created(delivery_table_name, orders_table_name, order, package_created_event):

    # create an order
    orders_table = boto3.resource("dynamodb").Table(orders_table_name)  # pylint: disable=no-member
    orders_table.put_item(Item=order)

    eventbridge = boto3.client("events")

    # Send the event on EventBridge
    eventbridge.put_events(Entries=[package_created_event])

    # Wait for PackageCreated event to be processed
    time.sleep(5)

    delivery_table = boto3.resource("dynamodb").Table(delivery_table_name)  # pylint: disable=no-member

    # Check DynamoDB delivery table to see that a delivery record was created
    results = delivery_table.query(
        KeyConditionExpression=Key("orderId").eq(order["orderId"])
    )

    # Assertions that a new package for delivery exists
    package = results.get("Items", [])
    assert len(package) == 1
    assert package[0]['isNew'] == 'true'
    assert package[0]['status'] == 'NEW'

    # Cleanup the tables
    orders_table.delete_item(Key={"orderId": order["orderId"]})
    delivery_table.delete_item(Key={"orderId": order["orderId"]})

