import asyncio
import pytest
from fixtures import context, lambda_module, get_order, get_product # pylint: disable=import-error
from helpers import compare_dict # pylint: disable=import-error,no-name-in-module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "create_order",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "TABLE_NAME": "TABLE_NAME",
        "USER_INDEX_NAME": "USER_INDEX_NAME",
        "ORDERS_LIMIT": "20",
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


def test_validate(lambda_module, order):
    """
    Test validate()
    """

    # TODO: mock APIs

    error_msgs = asyncio.run(lambda_module.validate(order))
    assert len(error_msgs) == 0