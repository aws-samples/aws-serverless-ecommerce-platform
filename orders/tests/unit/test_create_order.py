import asyncio
import copy
import json
from typing import Tuple
from botocore import stub
import pytest
import requests
import requests_mock
from fixtures import context, lambda_module, get_order, get_product # pylint: disable=import-error
from helpers import compare_dict, mock_table # pylint: disable=import-error,no-name-in-module


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
    assert new_order["total"] == sum([p["price"]*p.get("quantity", 1) for p in order["products"]]) + order["deliveryPrice"]


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


def test_validate_fail(monkeypatch, lambda_module, order):
    """
    Test validate() with failures
    """

    async def validate_true(order: dict) -> Tuple[bool, str]:
        return (False, "Something is wrong")

    monkeypatch.setattr(lambda_module, "validate_delivery", validate_true)
    monkeypatch.setattr(lambda_module, "validate_payment", validate_true)
    monkeypatch.setattr(lambda_module, "validate_products", validate_true)

    error_msgs = asyncio.run(lambda_module.validate(order))
    assert len(error_msgs) == 3


def test_store_order(lambda_module, order):
    """
    Test store_order()
    """

    table = mock_table(
        lambda_module.table, "put_item",
        ["orderId"],
        items=order
    )

    lambda_module.store_order(order)

    table.assert_no_pending_responses()
    table.deactivate()


def test_handler(monkeypatch, lambda_module, context, order):
    """
    Test handler()
    """

    async def validate_true(order: dict) -> Tuple[bool, str]:
        return (True, "")

    def store_order(order: dict) -> None:
        pass

    monkeypatch.setattr(lambda_module, "validate_delivery", validate_true)
    monkeypatch.setattr(lambda_module, "validate_payment", validate_true)
    monkeypatch.setattr(lambda_module, "validate_products", validate_true)
    monkeypatch.setattr(lambda_module, "store_order", store_order)

    user_id = order["userId"]
    order = copy.deepcopy(order)
    del order["userId"]

    response = lambda_module.handler({
        "order": order,
        "userId": user_id
    }, context)

    print(response)
    assert response["success"] == True
    assert len(response.get("errors", [])) == 0
    assert "order" in response
    compare_dict(order, response["order"])


def test_handler_wrong_event(monkeypatch, lambda_module, context, order):
    """
    Test handler() with an incorrect event
    """

    async def validate_true(order: dict) -> Tuple[bool, str]:
        return (True, "")

    def store_order(order: dict) -> None:
        pass

    monkeypatch.setattr(lambda_module, "validate_delivery", validate_true)
    monkeypatch.setattr(lambda_module, "validate_payment", validate_true)
    monkeypatch.setattr(lambda_module, "validate_products", validate_true)
    monkeypatch.setattr(lambda_module, "store_order", store_order)

    response = lambda_module.handler({
        "order": order
    }, context)

    print(response)
    assert response["success"] == False
    assert len(response.get("errors", [])) > 0


def test_handler_wrong_order(monkeypatch, lambda_module, context, order):
    """
    Test handler() with an incorrect order
    """

    async def validate_true(order: dict) -> Tuple[bool, str]:
        return (True, "")

    def store_order(order: dict) -> None:
        pass

    monkeypatch.setattr(lambda_module, "validate_delivery", validate_true)
    monkeypatch.setattr(lambda_module, "validate_payment", validate_true)
    monkeypatch.setattr(lambda_module, "validate_products", validate_true)
    monkeypatch.setattr(lambda_module, "store_order", store_order)

    user_id = order["userId"]
    order = copy.deepcopy(order)
    del order["userId"]
    del order["paymentToken"]

    response = lambda_module.handler({
        "order": order,
        "userId": user_id
    }, context)

    print(response)
    assert response["success"] == False
    assert len(response.get("errors", [])) > 0


def test_handler_validation_failure(monkeypatch, lambda_module, context, order):
    """
    Test handler() with failing validation
    """

    async def validate_true(order: dict) -> Tuple[bool, str]:
        return (False, "Something went wrong")

    def store_order(order: dict) -> None:
        pass

    monkeypatch.setattr(lambda_module, "validate_delivery", validate_true)
    monkeypatch.setattr(lambda_module, "validate_payment", validate_true)
    monkeypatch.setattr(lambda_module, "validate_products", validate_true)
    monkeypatch.setattr(lambda_module, "store_order", store_order)

    user_id = order["userId"]
    order = copy.deepcopy(order)
    del order["userId"]

    response = lambda_module.handler({
        "order": order,
        "userId": user_id
    }, context)

    print(response)
    assert response["success"] == False
    assert len(response.get("errors", [])) > 0