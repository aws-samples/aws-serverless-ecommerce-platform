import datetime
import os
import uuid
import boto3
import pytest
import requests
from fixtures import iam_auth # pylint: disable=import-error,no-name-in-module
from helpers import compare_dict, get_parameter # pylint: disable=import-error,no-name-in-module


ssm = boto3.client("ssm")


@pytest.fixture(scope="module")
def table_name():
    return get_parameter("/ecommerce/{Environment}/products/table/name")


@pytest.fixture(scope="module")
def endpoint_url():
    return get_parameter("/ecommerce/{Environment}/products/api/url")


@pytest.fixture(scope="module")
def product(table_name):

    now = datetime.datetime.now()

    product = {
        "productId": str(uuid.uuid4()),
        "createdDate": now.isoformat(),
        "modifiedDate": now.isoformat(),
        "name": "PRODUCT_NAME",
        "category": "PRODUCT_CATEGORY",
        "tags": ["TAG1", "TAG2", "TAG3"],
        "pictures": ["PICTURE1", "PICTURE2"],
        "package": {
            "width": 100,
            "length": 200,
            "height": 300,
            "weight": 400
        },
        "price": 500
    }

    # Create the product in DynamoDB
    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member
    table.put_item(Item=product)

    yield product

    # Delete the product in DynamoDB
    table.delete_item(Key={"productId": product["productId"]})


def test_get_product(endpoint_url, product):
    """
    Test GET /{productId}
    """

    res = requests.get("{}/{}".format(endpoint_url, product["productId"]))
    assert res.status_code == 200
    body = res.json()
    compare_dict(product, body)


def test_get_product_empty(endpoint_url, product):
    """
    Test GET /{productId} with a non-existing product
    """

    res = requests.get("{}/{}a".format(endpoint_url, product["productId"]))
    assert res.status_code == 404
    body = res.json()
    assert "message" in body
    assert isinstance(body["message"], str)