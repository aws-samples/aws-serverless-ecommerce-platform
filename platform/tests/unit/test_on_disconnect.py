import uuid
from botocore import stub
import pytest
from fixtures import apigateway_event, context, lambda_module # pylint: disable=import-error
from helpers import mock_table # pylint: disable=import-error,no-name-in-module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "on_disconnect",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "EVENT_RULE_NAME": "EVENT_BUS_NAME|EVENT_RULE_NAME",
        "LISTENER_TABLE_NAME": "TABLE_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


def test_delete_id(lambda_module):
    """
    Test delete_id()
    """

    connection_id = str(uuid.uuid4())
    table = mock_table(
        lambda_module.table, "delete_item", ["id"],
        items={"id": connection_id}
    )

    lambda_module.delete_id(connection_id)

    table.assert_no_pending_responses()
    table.deactivate()


def test_handler(monkeypatch, lambda_module, context, apigateway_event):
    """
    Test handler()
    """

    connection_id = str(uuid.uuid4())

    event = apigateway_event()
    event["requestContext"] = {"connectionId": connection_id}

    calls = {
        "delete_id": 0
    }

    def delete_id(connection_id_req: str):
        calls["delete_id"] += 1
        assert connection_id_req == connection_id
    monkeypatch.setattr(lambda_module, "delete_id", delete_id)

    result = lambda_module.handler(event, context)

    assert result["statusCode"] == 200
    assert calls["delete_id"] == 1


def test_handler_no_id(monkeypatch, lambda_module, context, apigateway_event):
    """
    Test handler()
    """

    connection_id = str(uuid.uuid4())

    event = apigateway_event()

    calls = {
        "delete_id": 0
    }

    def delete_id(connection_id_req: str):
        calls["delete_id"] += 1
        assert connection_id_req == connection_id
    monkeypatch.setattr(lambda_module, "delete_id", delete_id)

    result = lambda_module.handler(event, context)

    assert result["statusCode"] == 400
    assert calls["delete_id"] == 0