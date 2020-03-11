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
    # Add a new item
    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member
    table.put_item(Item=order)

    # Listen for messages on EventBridge through a listener SQS queue
    messages = listener("orders")

    # Parse messages
    found = False
    for message in messages:
        print("MESSAGE RECEIVED:", message)
        body = json.loads(message["Body"])
        if order["orderId"] in body["resources"]:
            found = True
            assert body["detail-type"] == "OrderCreated"

    assert found == True

    # Change the status to cancelled
    table.update_item(
        Key={"orderId": order["orderId"]},
        UpdateExpression="set #s = :s",
        ExpressionAttributeNames={
            "#s": "status"
        },
        ExpressionAttributeValues={
            ":s": "CANCELLED"
        }
    )

    # Listen for messages on EventBridge through a listener SQS queue
    messages = listener("orders")

    # Parse messages
    found = False
    for message in messages:
        print("MESSAGE RECEIVED:", message)
        body = json.loads(message["Body"])
        if order["orderId"] in body["resources"]:
            found = True
            assert body["detail-type"] == "OrderModified"
            detail = body["detail"]
            assert "changed" in detail
            assert "status" in detail["changed"]

    assert found == True

    # Delete the item
    table.delete_item(Key={"orderId": order["orderId"]})

    # Listen for messages on EventBridge through a listener SQS queue
    messages = listener("orders")

    # Parse messages
    found = False
    for message in messages:
        print("MESSAGE RECEIVED:", message)
        body = json.loads(message["Body"])
        if order["orderId"] in body["resources"]:
            found = True
            assert body["detail-type"] == "OrderDeleted"

    assert found == True