import json
import os
import uuid
import pytest
import boto3
from fixtures import listener # pylint: disable=import-error
from helpers import get_parameter # pylint: disable=import-error,no-name-in-module


@pytest.fixture
def table_name():
    """
    DynamoDB table name
    """

    return get_parameter("/ecommerce/{Environment}/products/table/name")


@pytest.fixture
def product():
    return {
        "productId": str(uuid.uuid4()),
        "name": "New product",
        "package": {
            "width": 200,
            "length": 100,
            "height": 50,
            "weight": 1000
        },
        "price": 500
    }


def test_table_update(table_name, listener, product):
    """
    Test that the TableUpdate function reacts to changes to DynamoDB and sends
    events to EventBridge
    """
    # Add a new item
    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member
    table.put_item(Item=product)

    # Listen for messages on EventBridge through a listener SQS queue
    messages = listener("products")

    # Parse messages
    found = False
    for message in messages:
        print("MESSAGE RECEIVED:", message)
        body = json.loads(message["Body"])
        if product["productId"] in body["resources"]:
            found = True
            assert body["detail-type"] == "ProductCreated"

    assert found == True

    # Delete the item
    table.delete_item(Key={"productId": product["productId"]})

    # Listen for messages on EventBridge through a listener SQS queue
    messages = listener("products")

    # Parse messages
    found = False
    for message in messages:
        print("MESSAGE RECEIVED:", message)
        body = json.loads(message["Body"])
        if product["productId"] in body["resources"]:
            found = True
            assert body["detail-type"] == "ProductDeleted"

    assert found == True