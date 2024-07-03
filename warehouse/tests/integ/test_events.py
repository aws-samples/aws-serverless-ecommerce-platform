import copy
import datetime
import json
import uuid
import boto3
import pytest
from fixtures import listener # pylint: disable=import-error
from helpers import get_parameter # pylint: disable=import-error


METADATA_KEY = "__metadata"


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
def metadata(order):
    return {
        "status": "NEW",
        "orderId": order["orderId"],
        "productId": METADATA_KEY,
        "modifiedDate": order["modifiedDate"]
    }

@pytest.fixture(scope="module")
def products(order):
    products = copy.deepcopy(order["products"])
    for product in products:
        product["orderId"] = order["orderId"]
    return products


def test_table_update(table_name, metadata, products, listener):
    """
    Test that the TableUpdate function reacts to changes to DynamoDB and sends
    events to EventBridge
    """

    metadata = copy.deepcopy(metadata)

    # Create packaging request in DynamoDB
    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member

    with table.batch_writer() as batch:
        for product in products:
            batch.put_item(Item=product)
        batch.put_item(Item=metadata)

    # Mark the packaging as completed
    metadata["status"] = "COMPLETED"
    

    # Listen for messages on EventBridge
    listener(
        "ecommerce.warehouse",
        lambda: table.put_item(Item=metadata),
        lambda m: metadata["orderId"] in m["resources"] and m["detail-type"] == "PackageCreated"
    )

    # Clean up the table
    with table.batch_writer() as batch:
        table.delete_item(Key={
            "orderId": metadata["orderId"],
            "productId": metadata["productId"]
        })
        for product in products:
            table.delete_item(Key={
                "orderId": product["orderId"],
                "productId": product["productId"]
            })