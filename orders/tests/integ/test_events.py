import datetime
import json
import uuid
import pytest
import boto3
from fixtures import get_order, get_product, listener # pylint: disable=import-error
from helpers import get_parameter # pylint: disable=import-error,no-name-in-module


@pytest.fixture
def table_name():
    """
    DynamoDB table name
    """

    return get_parameter("/ecommerce/{Environment}/orders/table/name")


@pytest.fixture
def order(get_order):
    return get_order()


def test_table_update(table_name, listener, order):
    """
    Test that the TableUpdate function reacts to changes to DynamoDB and sends
    events to EventBridge
    """
    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member

    # Listen for messages on EventBridge
    listener(
        "ecommerce.orders",
        # Add a new item
        lambda: table.put_item(Item=order),
        lambda m: order["orderId"] in m["resources"] and m["detail-type"] == "OrderCreated"
    )

    # Listen for messages on EventBridge
    listener(
        "ecommerce.orders",
        # Change the status to cancelled
        lambda: table.update_item(
            Key={"orderId": order["orderId"]},
            UpdateExpression="set #s = :s",
            ExpressionAttributeNames={
                "#s": "status"
            },
            ExpressionAttributeValues={
                ":s": "CANCELLED"
            }
        ),
        lambda m: order["orderId"] in m["resources"] and m["detail-type"] == "OrderModified"
    )

    # Listen for messages on EventBridge
    listener(
        "ecommerce.orders",
        # Delete the item
        lambda: table.delete_item(Key={"orderId": order["orderId"]}),
        lambda m: order["orderId"] in m["resources"] and m["detail-type"] == "OrderDeleted"
    )