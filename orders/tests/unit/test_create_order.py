import asyncio
import json
from typing import Tuple
import pytest
import requests
import requests_mock
from fixtures import context, lambda_module, get_order, get_product # pylint: disable=import-error
from helpers import compare_dict # pylint: disable=import-error,no-name-in-module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "create_order",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "PRODUCTS_API_URL": "mock://PRODUCTS_API_URL",
        "TABLE_NAME": "TABLE_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


@pytest.fixture
def order(get_order):
    """
    Order fixture
    """

    order = get_order()
    return {k: order[k] for k in [
        "userId", "products", "address", "deliveryPrice", "paymentToken"
    ]}


def test_inject_order_fields(lambda_module, order):
    """
    Test inject_order_fields()
    """

    new_order = lambda_module.inject_order_fields(order)

    assert "orderId" in new_order
    assert "createdDate" in new_order
    assert "modifiedDate" in new_order
    assert "total" in new_order


def test_validate_products(lambda_module, order):
    """
    Test validate_products()
    """

    url = "mock://PRODUCTS_API_URL/backend/validate"

    with requests_mock.Mocker() as m:
        m.post(url, text=json.dumps({"message": "All products are valid"}))

        valid, error_msg = asyncio.run(lambda_module.validate_products(order))

    print(valid, error_msg)

    assert m.called
    assert m.call_count == 1
    assert m.request_history[0].method == "POST"
    assert m.request_history[0].url == url
    assert valid == True
    assert error_msg == "All products are valid"


def test_validate_products_fail(lambda_module, order):
    """
    Test validate_products() failing
    """

    url = "mock://PRODUCTS_API_URL/backend/validate"

    with requests_mock.Mocker() as m:
        m.post(
            url,
            text=json.dumps({"message": "Something is wrong", "products": order["products"]}),
            status_code=400
        )

        valid, error_msg = asyncio.run(lambda_module.validate_products(order))

    print(valid, error_msg)

    assert m.called
    assert m.call_count == 1
    assert m.request_history[0].method == "POST"
    assert m.request_history[0].url == url
    assert valid == False
    assert error_msg == "Something is wrong"



def test_validate(monkeypatch, lambda_module, order):
    """
    Test validate()
    """

    async def validate_true(order: dict) -> Tuple[bool, str]:
        return (True, "")

    monkeypatch.setattr(lambda_module, "validate_delivery", validate_true)
    monkeypatch.setattr(lambda_module, "validate_payment", validate_true)
    monkeypatch.setattr(lambda_module, "validate_products", validate_true)

    error_msgs = asyncio.run(lambda_module.validate(order))
    assert len(error_msgs) == 0