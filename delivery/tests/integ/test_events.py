import json
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

    return get_parameter("/ecommerce/{Environment}/delivery/table/name")


@pytest.fixture
def order():
    return {
        "orderId": str(uuid.uuid4()),
        "address": {
            "name": "John Doe",
            "companyName": "Company Inc.",
            "streetAddress": "123 Street St",
            "postCode": "12345",
            "city": "Town",
            "state": "State",
            "country": "SE",
            "phoneNumber": "+123456789"
        }
    }


def test_table_update_completed(table_name, listener, order):
    """
    Test that the TableUpdate function reacts to changes to DynamoDB and sends events to EventBridge
    """

    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member

    # Add a new item
    order["status"] = "IN_PROGRESS"
    table.put_item(Item=order)

    # Set the item to COMPLETED
    order["status"] = "COMPLETED"

    # Listen for messages on EventBridge
    listener(
        "ecommerce.delivery",
        lambda: table.put_item(Item=order),
        lambda m: order["orderId"] in m["resources"] and m["detail-type"] == "DeliveryCompleted"
    )

    # Delete the item
    table.delete_item(Key={"orderId": order["orderId"]})


def test_table_update_failed(table_name, listener, order):
    """
    Test that the TableUpdate function reacts to changes to DynamoDB and sends events to EventBridge
    """

    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member

    # Add a new item
    order["status"] = "NEW"
    table.put_item(Item=order)

    # Listen for messages on EventBridge through a listener SQS queue
    listener(
        "ecommerce.delivery",
        lambda: table.delete_item(Key={"orderId": order["orderId"]}),
        lambda m: order["orderId"] in m["resources"] and m["detail-type"] == "DeliveryFailed"
    )