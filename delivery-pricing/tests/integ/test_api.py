import pytest
import requests
from fixtures import get_order, get_product, iam_auth # pylint: disable=import-error,no-name-in-module
from helpers import compare_dict, get_parameter # pylint: disable=import-error,no-name-in-module


@pytest.fixture(scope="module")
def endpoint_url():
    return get_parameter("/ecommerce/{Environment}/delivery-pricing/api/url")


@pytest.fixture(scope="function")
def order(get_order):
    return get_order()


def test_backend_pricing(endpoint_url, iam_auth, order):
    """
    Test POST /backend/pricing
    """

    res = requests.post(
        "{}/backend/pricing".format(endpoint_url),
        auth=iam_auth(endpoint_url),
        json={
            "products": order["products"],
            "address": order["address"]
        }
    )

    assert res.status_code == 200
    body = res.json()
    assert "pricing" in body


def test_backend_pricing_no_iam(endpoint_url, iam_auth, order):
    """
    Test POST /backend/pricing
    """

    res = requests.post(
        "{}/backend/pricing".format(endpoint_url),
        json={
            "products": order["products"],
            "address": order["address"]
        }
    )

    assert res.status_code == 403
    body = res.json()
    assert "message" in body
    assert isinstance(body["message"], str)


def test_backend_pricing_no_products(endpoint_url, iam_auth, order):
    """
    Test POST /backend/pricing
    """

    res = requests.post(
        "{}/backend/pricing".format(endpoint_url),
        auth=iam_auth(endpoint_url),
        json={
            "address": order["address"]
        }
    )

    assert res.status_code == 400
    body = res.json()
    assert "message" in body
    assert isinstance(body["message"], str)
    assert "products" in body["message"]


def test_backend_pricing_no_address(endpoint_url, iam_auth, order):
    """
    Test POST /backend/pricing
    """

    res = requests.post(
        "{}/backend/pricing".format(endpoint_url),
        auth=iam_auth(endpoint_url),
        json={
            "products": order["products"]
        }
    )

    assert res.status_code == 400
    body = res.json()
    assert "message" in body
    assert isinstance(body["message"], str)
    assert "address" in body["message"]