import datetime
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

    return get_parameter("/ecommerce/{Environment}/orders/table/name")


@pytest.fixture
def order():
    now = datetime.datetime.now()

    return {
        "orderId": str(uuid.uuid4()),
        "userId": str(uuid.uuid4()),
        "createdDate": now.isoformat(),
        "modifiedDate": now.isoformat(),
        "status": "NEW",
        "products": [{
            "productId": str(uuid.uuid4()),
            "name": "Test Product",
            "package": {
                "width": 1000,
                "length": 900,
                "height": 800,
                "weight": 700
            },
            "price": 300,
            "quantity": 4
        }],
        "address": {
            "name": "John Doe",
            "companyName": "Company Inc.",
            "streetAddress": "123 Street St",
            "postCode": "12345",
            "city": "Town",
            "state": "State",
            "country": "SE",
            "phoneNumber": "+123456789"
        },
        "deliveryPrice": 200,
        "total": 1400
    }


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
