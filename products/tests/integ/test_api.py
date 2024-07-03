import copy
import datetime
import os
import uuid
import boto3
import pytest
import requests
from fixtures import iam_auth # pylint: disable=import-error,no-name-in-module
from helpers import compare_dict, get_parameter # pylint: disable=import-error,no-name-in-module


@pytest.fixture(scope="module")
def table_name():
    return get_parameter("/ecommerce/{Environment}/products/table/name")


@pytest.fixture(scope="module")
def endpoint_url():
    return get_parameter("/ecommerce/{Environment}/products/api/url")


@pytest.fixture(scope="function")
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
def test_backend_validate(endpoint_url, iam_auth, product):
    """
    Test POST /backend/validate
    """

    res = requests.post(
        "{}/backend/validate".format(endpoint_url),
        auth=iam_auth(endpoint_url),
        json={"products": [product]}
    )

    assert res.status_code == 200
    body = res.json()
    assert "products" not in body


def test_backend_validate_no_iam(endpoint_url, product):
    """
    Test POST /backend/validate without IAM auth
    """

    res = requests.post(
        "{}/backend/validate".format(endpoint_url),
        json={"products": [product]}
    )

    assert res.status_code == 403
    body = res.json()
    assert "message" in body
    assert isinstance(body["message"], str)


def test_backend_validate_incorrect_price(endpoint_url, iam_auth, product):
    """
    Test POST /backend/validate with an incorrect product
    """

    wrong_product = copy.deepcopy(product)

    wrong_product["price"] += 100

    res = requests.post(
        "{}/backend/validate".format(endpoint_url),
        auth=iam_auth(endpoint_url),
        json={"products": [wrong_product]}
    )

    assert res.status_code == 200
    body = res.json()
    assert "products" in body
    assert len(body["products"]) == 1
    compare_dict(body["products"][0], product)


def test_backend_validate_incorrect_package(endpoint_url, iam_auth, product):
    """
    Test POST /backend/validate with an incorrect product
    """

    wrong_product = copy.deepcopy(product)

    wrong_product["package"]["height"] += 100

    res = requests.post(
        "{}/backend/validate".format(endpoint_url),
        auth=iam_auth(endpoint_url),
        json={"products": [wrong_product]}
    )

    assert res.status_code == 200
    body = res.json()
    assert "products" in body
    assert len(body["products"]) == 1
    compare_dict(body["products"][0], product)


def test_backend_validate_incorrect_pictures(endpoint_url, iam_auth, product):
    """
    Test POST /backend/validate with an incorrect product
    """

    wrong_product = copy.deepcopy(product)

    wrong_product["pictures"].append("INCORRECT_PICTURE")

    res = requests.post(
        "{}/backend/validate".format(endpoint_url),
        auth=iam_auth(endpoint_url),
        json={"products": [wrong_product]}
    )

    assert res.status_code == 200
    body = res.json()
    assert "products" not in body


def test_backend_validate_mixed(endpoint_url, iam_auth, product):
    """
    Test /backend/validate with a mix of correct and incorrect product
    """

    wrong_product = copy.deepcopy(product)
    wrong_product["price"] += 100

    res = requests.post(
        "{}/backend/validate".format(endpoint_url),
        auth=iam_auth(endpoint_url),
        json={"products": [product, wrong_product]}
    )

    assert res.status_code == 200
    body = res.json()
    assert "products" in body
    assert len(body["products"]) == 1
    compare_dict(body["products"][0], product)