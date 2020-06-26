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

    # Listen for messages on EventBridge
    listener(
        "ecommerce.products",
        lambda: table.put_item(Item=product),
        lambda m: product["productId"] in m["resources"] and m["detail-type"] == "ProductCreated"
    )

    # Listen for messages on EventBridge
    listener(
        "ecommerce.products",
        lambda: table.delete_item(Key={"productId": product["productId"]}),
        lambda m: product["productId"] in m["resources"] and m["detail-type"] == "ProductDeleted"
    )