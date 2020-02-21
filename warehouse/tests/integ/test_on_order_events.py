import copy
import datetime
import json
import time
import uuid
import boto3
from boto3.dynamodb.conditions import Key
import pytest
from helpers import get_parameter # pylint: disable=import-error


METADATA_KEY = "__metadata"


@pytest.fixture(scope="module")
def event_bus_name():
    """
    EventBridge Event Bus name
    """

    return get_parameter("/ecommerce/{Environment}/platform/event-bus/name")


@pytest.fixture(scope="module")
def table_name():
    """
    DynamoDB table name
    """

    return get_parameter("/ecommerce/{Environment}/warehouse/table/name")


@pytest.fixture(scope="module")
def order():
    now = datetime.datetime.now()
    return {
        "orderId": str(uuid.uuid4()),
        "userId": str(uuid.uuid4()),
        "createdDate": now.isoformat(),
        "modifiedDate": now.isoformat(),
        "products": [{
            "productId": str(uuid.uuid4()),
            "name": "PRODUCT_NAME",
            "package": {
                "width": 200,
                "length": 100,
                "height": 50,
                "weight": 1000
            },
            "price": 500,
            "quantity": 3
        }]
    }


@pytest.fixture(scope="module")
def order_event(order, event_bus_name):
    return {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.orders",
        "Resources": [order["orderId"]],
        "DetailType": "OrderCreated",
        "Detail": json.dumps(order),
        "EventBusName": event_bus_name
    }


@pytest.fixture(scope="module")
def metadata(order):
    return {
        "status": "NEW",
        "orderId": order["orderId"],
        "productId": METADATA_KEY,
        "modifiedDate": order["modifiedDate"]
    }

@pytest.fixture(scope="module")
def products(order):
    products = []
    for product in order["products"]:
        products.append({
            "orderId": order["orderId"],
            "productId": product["productId"],
            "quantity": product["quantity"]
        })
    return products


def test_on_order_events(order_event, table_name, order, metadata, products):
    """
    Test if received Order Events create resources in DynamoDB
    """

    # Send the event on EventBridge
    eventbridge = boto3.client("events")
    eventbridge.put_events(Entries=[order_event])

    # Wait
    time.sleep(10)

    # Check DynamoDB
    table = boto3.resource("dynamodb").Table(table_name)
    results = table.query(
        KeyConditionExpression=Key("orderId").eq(order["orderId"])
    )

    # Assertions
    assert len(results.get("Items", [])) == 1+len(products)

    has_metadata = False
    product_founds = {}
    for item in results.get("Items", []):
        if item["productId"] == METADATA_KEY:
            has_metadata = True
            assert metadata == item
        else:
            product_founds[item["productId"]] = item

    assert has_metadata
    for product in products:
        assert product["productId"] in product_founds
        assert product == product_founds[product["productId"]]

    with table.batch_writer() as batch:
        batch.delete_item(Key={
            "orderId": metadata["orderId"],
            "productId": metadata["productId"]
        })
        for product in product_founds.values():
            batch.delete_item(Key={
                "orderId": product["orderId"],
                "productId": product["productId"]
            })