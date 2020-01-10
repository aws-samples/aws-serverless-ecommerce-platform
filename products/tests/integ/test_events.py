import json
import os
import uuid
import boto3
import pytest


ssm = boto3.client("ssm")


QUEUE_URL = ssm.get_parameter(Name="/ecommerce/products/listener/url")["Parameter"]["Value"]
TABLE_NAME = ssm.get_parameter(Name="/ecommerce/products/table/name")["Parameter"]["Value"]
EVENT_SOURCE = "ecommerce.products"
TIMEOUT = 60 # time in seconds


sqs = boto3.client("sqs")
table = boto3.resource("dynamodb").Table(TABLE_NAME)


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


def test_table_update(product):
    table.put_item(Item=product)

    messages = []
    for i in range(TIMEOUT//20):
        retval = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            WaitTimeSeconds=20
        )
        messages.extend(retval.get("Messages", []))

    found = False
    for message in messages:
        print("MESSAGE RECEIVED:", message)
        body = json.loads(message["Body"])
        if product["productId"] not in body["resources"]:
            continue
        else:
            found = True
            assert body["detail-type"] == "ProductCreated"

    assert found == True