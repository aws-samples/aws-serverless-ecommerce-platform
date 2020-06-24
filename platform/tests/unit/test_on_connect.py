import uuid
from botocore import stub
import pytest
from fixtures import apigateway_event, context, lambda_module # pylint: disable=import-error
from helpers import mock_table # pylint: disable=import-error,no-name-in-module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "on_connect",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "EVENT_RULE_NAME": "EVENT_BUS_NAME|EVENT_RULE_NAME",
        "LISTENER_TABLE_NAME": "TABLE_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


def test_store_id(lambda_module):
    """
    Test store_id()
    """

    connection_id = str(uuid.uuid4())
    table = mock_table(
        lambda_module.table, "put_item", ["id"],
        items={
            "id": connection_id,
            "ttl": stub.ANY
        }
    )

    lambda_module.store_id(connection_id)

    table.assert_no_pending_responses()
    table.deactivate()


def test_enable_rule(lambda_module):
    """
    Test enable_rule()
    """

    eventbridge = stub.Stubber(lambda_module.eventbridge)
    eventbridge.add_response("enable_rule", {}, {
        "Name": "EVENT_RULE_NAME",
        "EventBusName": "EVENT_BUS_NAME"
    })
    eventbridge.activate()

    lambda_module.enable_rule()

    eventbridge.assert_no_pending_responses()

    eventbridge.deactivate()


def test_handler(monkeypatch, lambda_module, context, apigateway_event):
    """
    Test handler()
    """

    connection_id = str(uuid.uuid4())

    event = apigateway_event()
    event["requestContext"] = {"connectionId": connection_id}

    calls = {
        "store_id": 0,
        "enable_rule": 0
    }

    def store_id(connection_id_req: str):
        calls["store_id"] += 1
        assert connection_id_req == connection_id
    monkeypatch.setattr(lambda_module, "store_id", store_id)

    def enable_rule():
        calls["enable_rule"] += 1
    monkeypatch.setattr(lambda_module, "enable_rule", enable_rule)

    result = lambda_module.handler(event, context)

    assert result["statusCode"] == 200
    assert calls["store_id"] == 1
    assert calls["enable_rule"] == 1


def test_handler_no_id(monkeypatch, lambda_module, context, apigateway_event):
    """
    Test handler()
    """

    connection_id = str(uuid.uuid4())

    event = apigateway_event()

    calls = {
        "store_id": 0,
        "enable_rule": 0
    }

    def store_id(connection_id_req: str):
        calls["store_id"] += 1
        assert connection_id_req == connection_id
    monkeypatch.setattr(lambda_module, "store_id", store_id)

    def enable_rule():
        calls["enable_rule"] += 1
    monkeypatch.setattr(lambda_module, "enable_rule", enable_rule)

    result = lambda_module.handler(event, context)

    assert result["statusCode"] == 400
    assert calls["store_id"] == 0
    assert calls["enable_rule"] == 0