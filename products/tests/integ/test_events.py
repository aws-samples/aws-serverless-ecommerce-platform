import json
import os
import uuid
import boto3
import pytest
from fixtures import listener


listener = pytest.fixture(scope="module", params=[{
    "service": "products"
}])(listener)


ssm = boto3.client("ssm")


TABLE_NAME = ssm.get_parameter(
    Name="/ecommerce/{}/products/table/name".format(os.environ["ECOM_ENVIRONMENT"])
)["Parameter"]["Value"]
EVENT_SOURCE = "ecommerce.products"
TIMEOUT = 60 # time in seconds


sqs = boto3.client("sqs")
table = boto3.resource("dynamodb").Table(TABLE_NAME) # pylint: disable=no-member


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


def test_table_update(listener, product):
    """
    Test that the TableUpdate function reacts to changes to DynamoDB and sends
    events to EventBridge
    """
    # Add a new item
    table.put_item(Item=product)

    # Listen for messages on EventBridge through a listener SQS queue
    messages = listener()

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
    messages = listener()

    # Parse messages
    found = False
    for message in messages:
        print("MESSAGE RECEIVED:", message)
        body = json.loads(message["Body"])
        if product["productId"] in body["resources"]:
            found = True
            assert body["detail-type"] == "ProductDeleted"

    assert found == True