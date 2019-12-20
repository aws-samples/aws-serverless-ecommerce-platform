import json
import os
from urllib.parse import urlparse
from aws_requests_auth.aws_auth import AWSRequestsAuth
import pytest
import requests


ENDPOINT_URL = os.environ["ENDPOINT_URL"]
PATH = "/backend/validate"

DIR_NAME = os.path.dirname(__file__)


@pytest.fixture
def iam_auth():
    """
    Helper function to return auth for IAM
    """

    url = urlparse(ENDPOINT_URL)

    return AWSRequestsAuth(aws_host=url.netloc,
                           aws_region=os.environ["AWS_REGION"],
                           aws_service='execute-api')


@pytest.fixture
def correct_product():
    with open(os.path.join(DIR_NAME, "data", "correct_product.json")) as fp:
        return json.load(fp)


@pytest.fixture
def incorrect_product_price():
    with open(os.path.join(DIR_NAME, "data", "correct_product.json")) as fp:
        product = json.load(fp)

    product["price"] += 200

    return product


@pytest.fixture
def incorrect_product_length():
    with open(os.path.join(DIR_NAME, "data", "correct_product.json")) as fp:
        product = json.load(fp)

    product["package"]["length"] += 200

    return product


@pytest.fixture
def incorrect_product_weight():
    with open(os.path.join(DIR_NAME, "data", "correct_product.json")) as fp:
        product = json.load(fp)

    product["package"]["weight"] += 200

    return product


def test_backend_validate_iam_fail():
    """
    Test that the API endpoints fails without IAM signature
    """

    response = requests.post(ENDPOINT_URL+PATH, json={})

    # Assertions
    assert response.status_code == 403


def test_backend_validate_iam_success(iam_auth):
    """
    Test that the API endpoints works with IAM signature
    """

    response = requests.post(ENDPOINT_URL+PATH, auth=iam_auth, json={})

    # Assertions
    assert response.status_code != 403


def test_backend_validate_empty(iam_auth):
    """
    Test behavior with an empty set of products
    """

    req_body = {"products": []}
    response = requests.post(ENDPOINT_URL+PATH, auth=iam_auth, json=req_body)

    # Assertions
    assert response.status_code == 200

    res_body = response.json()
    assert "products" in res_body
    assert len(res_body["products"]) == 0


def test_backend_validate_correct(iam_auth, correct_product):
    """
    Test behavior with a correct product
    """

    req_body = {"products": [correct_product]}
    response = requests.post(ENDPOINT_URL+PATH, auth=iam_auth, json=req_body)

    # Assertions
    assert response.status_code == 200

    res_body = response.json()
    assert "products" in res_body
    assert len(res_body["products"]) == 0


def test_backend_validate_incorrect_price(iam_auth, correct_product, incorrect_product_price):
    """
    Test behavior with an incorrect product price
    """

    req_body = {"products": [incorrect_product_price]}
    response = requests.post(ENDPOINT_URL+PATH, auth=iam_auth, json=req_body)

    # Assertions
    assert response.status_code == 400

    res_body = response.json()
    assert "products" in res_body
    assert len(res_body["products"]) == 1
    assert res_body["products"][0] == correct_product


def test_backend_validate_incorrect_length(iam_auth, correct_product, incorrect_product_length):
    """
    Test behavior with an incorrect product length
    """

    req_body = {"products": [incorrect_product_length]}
    response = requests.post(ENDPOINT_URL+PATH, auth=iam_auth, json=req_body)

    # Assertions
    assert response.status_code == 400

    res_body = response.json()
    assert "products" in res_body
    assert len(res_body["products"]) == 1
    assert res_body["products"][0] == correct_product


def test_backend_validate_incorrect_weight(iam_auth, correct_product, incorrect_product_weight):
    """
    Test behavior with an incorrect product weight
    """

    req_body = {"products": [incorrect_product_weight]}
    response = requests.post(ENDPOINT_URL+PATH, auth=iam_auth, json=req_body)

    # Assertions
    assert response.status_code == 400

    res_body = response.json()
    assert "products" in res_body
    assert len(res_body["products"]) == 1
    assert res_body["products"][0] == correct_product


def test_backend_validate_mixed(iam_auth, correct_product, incorrect_product_price):
    """
    Test behavior with a mix of correct and incorrect products
    """

    req_body = {"products": [correct_product, incorrect_product_price]}
    response = requests.post(ENDPOINT_URL+PATH, auth=iam_auth, json=req_body)

    # Assertions
    assert response.status_code == 400

    res_body = response.json()
    assert "products" in res_body
    assert len(res_body["products"]) == 1
    assert res_body["products"][0] == correct_product
