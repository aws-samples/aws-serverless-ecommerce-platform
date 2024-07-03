import uuid
import pytest
from fixtures import context, lambda_module # pylint: disable=import-error
from helpers import mock_table # pylint: disable=import-error,no-name-in-module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "on_created",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "TABLE_NAME": "TABLE_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


@pytest.fixture
def order_id():
    return str(uuid.uuid4())

@pytest.fixture
def payment_token():
    return str(uuid.uuid4())


def test_save_payment_token(lambda_module, order_id, payment_token):
    """
    Test save_payment_token()
    """

    table = mock_table(
        lambda_module.table,
        action="put_item",
        keys=["orderId"],
        items={"orderId": order_id, "paymentToken": payment_token}
    )

    lambda_module.save_payment_token(order_id, payment_token)

    table.assert_no_pending_responses()
    table.deactivate()


def test_handler(monkeypatch, lambda_module, context, order_id, payment_token):
    """
    Test handler()
    """

    event = {
        "source": "ecommerce.orders",
        "detail-type": "OrderCreated",
        "resources": [order_id],
        "detail": {
            "orderId": order_id,
            "paymentToken": payment_token
        }
    }

    def save_payment_token(o: str, p: str):
        assert o == order_id
        assert p == payment_token

    monkeypatch.setattr(lambda_module, "save_payment_token", save_payment_token)

    lambda_module.handler(event, context)