import json
import requests
import requests_mock
import uuid
import pytest
from fixtures import context, lambda_module # pylint: disable=import-error
from helpers import mock_table # pylint: disable=import-error,no-name-in-module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "on_completed",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "TABLE_NAME": "TABLE_NAME",
        "API_URL": "mock://API_URL",
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


def test_get_payment_token(lambda_module, order_id, payment_token):
    """
    Test get_payment_token()
    """

    table = mock_table(
        lambda_module.table,
        action="get_item",
        keys=["orderId"],
        items={"orderId": order_id, "paymentToken": payment_token}
    )

    response = lambda_module.get_payment_token(order_id)

    assert response == payment_token

    table.assert_no_pending_responses()
    table.deactivate()


def test_get_payment_token_no_item(lambda_module, order_id, payment_token):
    """
    Test get_payment_token() without an item
    """

    table = mock_table(
        lambda_module.table,
        action="get_item",
        keys=["orderId"]
    )

    try:
        lambda_module.get_payment_token(order_id)
        assert 1 == 2
    except:
        pass

    table.assert_no_pending_responses()
    table.deactivate()


def test_delete_payment_token(lambda_module, order_id, payment_token):
    """
    Test delete_payment_token()
    """

    table = mock_table(
        lambda_module.table,
        action="delete_item",
        keys=["orderId"],
        items={"orderId": order_id, "paymentToken": payment_token}
    )

    lambda_module.delete_payment_token(order_id)

    table.assert_no_pending_responses()
    table.deactivate()


def test_process_payment(lambda_module, payment_token):
    """
    Test process_payment()
    """

    url = "mock://API_URL/processPayment"

    with requests_mock.Mocker() as m:
        m.post(url, text=json.dumps({"ok": True}))

        lambda_module.process_payment(payment_token)

    assert m.called
    assert m.call_count == 1
    assert m.request_history[0].method == "POST"
    assert m.request_history[0].url == url


def test_process_payment_failed(lambda_module, payment_token):
    """
    Test process_payment() with a failed attempt
    """

    url = "mock://API_URL/processPayment"

    with requests_mock.Mocker() as m:
        m.post(url, text=json.dumps({"message": "ERROR_MESSAGE"}))

        try:
            lambda_module.process_payment(payment_token)
            assert 1 == 2
        except Exception as exc:
            assert "ERROR_MESSAGE" in str(exc)

    assert m.called
    assert m.call_count == 1
    assert m.request_history[0].method == "POST"
    assert m.request_history[0].url == url


def test_handler(monkeypatch, lambda_module, context, order_id, payment_token):
    """
    Test handler()
    """

    event = {
        "source": "ecommerce.delivery",
        "detail-type": "DeliveryCompleted",
        "resources": [order_id],
        "detail": {
            "orderId": order_id,
            "total": 2345
        }
    }

    called = []
    def process_payment(p: str) -> None:
        called.append("process_payment")
        assert p == payment_token

    def get_payment_token(o: str) -> str:
        called.append("get_payment_token")
        assert o == order_id
        return payment_token

    def delete_payment_token(o: str) -> str:
        called.append("delete_payment_token")
        assert o == order_id

    monkeypatch.setattr(lambda_module, "get_payment_token", get_payment_token)
    monkeypatch.setattr(lambda_module, "delete_payment_token", delete_payment_token)
    monkeypatch.setattr(lambda_module, "process_payment", process_payment)

    lambda_module.handler(event, context)

    assert "process_payment" in called
    assert "get_payment_token" in called
    assert "delete_payment_token" in called