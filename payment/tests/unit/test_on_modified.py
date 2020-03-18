import json
import uuid
import pytest
import requests
import requests_mock
from fixtures import context, lambda_module # pylint: disable=import-error
from helpers import mock_table # pylint: disable=import-error,no-name-in-module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "on_modified",
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


def test_update_payment_amount(lambda_module, payment_token):
    """
    Test update_payment_amount()
    """

    url = "mock://API_URL/updateAmount"

    with requests_mock.Mocker() as m:
        m.post(url, text=json.dumps({"ok": True}))

        lambda_module.update_payment_amount(payment_token, 200)

    assert m.called
    assert m.call_count == 1
    assert m.request_history[0].method == "POST"
    assert m.request_history[0].url == url


def test_update_payment_amount_failed(lambda_module, payment_token):
    """
    Test update_payment_amount() with a failed request
    """

    url = "mock://API_URL/updateAmount"

    with requests_mock.Mocker() as m:
        m.post(url, text=json.dumps({"message": "ERROR_MESSAGE"}))

        try:
            lambda_module.update_payment_amount(payment_token, 200)
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
        "detail-type": "DeliveryFailed",
        "resources": [order_id],
        "detail": {
            "old": {
                "orderId": order_id,
                "total": 300
            },
            "new": {
                "orderId": order_id,
                "total": 200
            }
        }
    }

    called = []
    def update_payment_amount(p: str, a: int) -> None:
        called.append("update_payment_amount")
        assert a == 200
        assert p == payment_token

    def get_payment_token(o: str) -> str:
        called.append("get_payment_token")
        assert o == order_id
        return payment_token


    monkeypatch.setattr(lambda_module, "get_payment_token", get_payment_token)
    monkeypatch.setattr(lambda_module, "update_payment_amount", update_payment_amount)

    lambda_module.handler(event, context)

    assert "update_payment_amount" in called
    assert "get_payment_token" in called
