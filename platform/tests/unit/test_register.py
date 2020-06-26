import json
import uuid
from botocore import stub
import pytest
from fixtures import apigateway_event, context, lambda_module # pylint: disable=import-error
from helpers import mock_table # pylint: disable=import-error,no-name-in-module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "register",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "LISTENER_TABLE_NAME": "TABLE_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


def test_register_service(lambda_module):
    """
    Test register_service()
    """

    connection_id = str(uuid.uuid4())
    service_name = "test"
    table = mock_table(
        lambda_module.table, "put_item", ["id"],
        items={
            "id": connection_id,
            "service": service_name,
            "ttl": stub.ANY
        }
    )

    lambda_module.register_service(connection_id, service_name)

    table.assert_no_pending_responses()
    table.deactivate()


def test_handler(monkeypatch, lambda_module, context, apigateway_event):
    """
    Test handler()
    """

    connection_id = str(uuid.uuid4())
    service_name = "ecommerce.test"

    event = apigateway_event()
    event["requestContext"] = {"connectionId": connection_id}
    event["body"] = json.dumps({"serviceName": service_name})

    calls = {
        "register_service": 0
    }

    def register_service(connection_id_req: str, service_name_req: str):
        calls["register_service"] += 1
        assert connection_id_req == connection_id
        assert service_name_req == service_name
    monkeypatch.setattr(lambda_module, "register_service", register_service)

    result = lambda_module.handler(event, context)

    assert result["statusCode"] == 200
    assert calls["register_service"] == 1


def test_handler_no_id(monkeypatch, lambda_module, context, apigateway_event):
    """
    Test handler() without connectionId
    """

    connection_id = str(uuid.uuid4())
    service_name = "ecommerce.test"

    event = apigateway_event()
    event["body"] = json.dumps({"serviceName": service_name})

    calls = {
        "register_service": 0
    }

    def register_service(connection_id_req: str, service_name_req: str):
        calls["register_service"] += 1
        assert connection_id_req == connection_id
        assert service_name_req == service_name
    monkeypatch.setattr(lambda_module, "register_service", register_service)

    result = lambda_module.handler(event, context)

    assert result["statusCode"] == 400
    assert calls["register_service"] == 0


def test_handler_invalid_body(monkeypatch, lambda_module, context, apigateway_event):
    """
    Test handler() without a correct JSON body
    """

    connection_id = str(uuid.uuid4())
    service_name = "ecommerce.test"

    event = apigateway_event()
    event["requestContext"] = {"connectionId": connection_id}
    event["body"] = "{"

    calls = {
        "register_service": 0
    }

    def register_service(connection_id_req: str, service_name_req: str):
        calls["register_service"] += 1
        assert connection_id_req == connection_id
        assert service_name_req == service_name
    monkeypatch.setattr(lambda_module, "register_service", register_service)

    result = lambda_module.handler(event, context)

    assert result["statusCode"] == 400
    assert calls["register_service"] == 0


def test_handler_no_service(monkeypatch, lambda_module, context, apigateway_event):
    """
    Test handler() without serviceName in body
    """

    connection_id = str(uuid.uuid4())
    service_name = "ecommerce.test"

    event = apigateway_event()
    event["requestContext"] = {"connectionId": connection_id}
    event["body"] = "{}"

    calls = {
        "register_service": 0
    }

    def register_service(connection_id_req: str, service_name_req: str):
        calls["register_service"] += 1
        assert connection_id_req == connection_id
        assert service_name_req == service_name
    monkeypatch.setattr(lambda_module, "register_service", register_service)

    result = lambda_module.handler(event, context)

    assert result["statusCode"] == 400
    assert calls["register_service"] == 0