import datetime
import os
import random
import string
import uuid
import boto3
import pytest
import requests
from urllib.parse import urlparse
from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
from helpers import compare_dict, get_parameter # pylint: disable=no-name-in-module


@pytest.fixture(scope="module")
def table_name():
    """
    DynamoDB table name
    """

    return get_parameter("/ecommerce/{Environment}/orders/table/name")


@pytest.fixture(scope="module")
def endpoint_url():
    """
    API Gateway Endpoint URL
    """

    return get_parameter("/ecommerce/{Environment}/orders/api/url")


@pytest.fixture(scope="module")
def order(table_name):
    """
    Order as stored in DynamoDB
    """

    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member


    now = datetime.datetime.now()

    order = {
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

    table.put_item(Item=order)

    yield order

    table.delete_item(
        Key={"orderId": order["orderId"]}
    )


@pytest.fixture
def iam_auth(endpoint_url):
    """
    Helper function to return auth for IAM
    """

    url = urlparse(endpoint_url)
    region = boto3.session.Session().region_name

    return BotoAWSRequestsAuth(aws_host=url.netloc,
                               aws_region=region,
                               aws_service='execute-api')


def test_get_backend_order(endpoint_url, iam_auth, order):
    """
    Test GET /backend/{orderId}
    """

    res = requests.get(endpoint_url+"/backend/"+order["orderId"], auth=iam_auth)
    assert res.status_code == 200
    body = res.json()
    compare_dict(order, body)


def test_get_backend_order_no_auth(endpoint_url, iam_auth, order):
    """
    Test GET /backend/{orderId} without auth
    """

    res = requests.get(endpoint_url+"/backend/"+order["orderId"])
    assert res.status_code == 403
    body = res.json()
    assert "message" in body
    assert isinstance(body["message"], str)


def test_get_backend_order_wrong_id(endpoint_url, iam_auth, order):
    """
    Test GET /backend/{orderId} with a non-existent orderId
    """

    res = requests.get(endpoint_url+"/backend/"+order["orderId"]+"a", auth=iam_auth)
    assert res.status_code == 404
    body = res.json()
    assert "message" in body
    assert isinstance(body["message"], str)