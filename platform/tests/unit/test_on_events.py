import json
from typing import List
import uuid
from boto3.dynamodb.types import TypeSerializer
from botocore import stub
import pytest
from fixtures import context, lambda_module # pylint: disable=import-error


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "on_events",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "LISTENER_TABLE_NAME": "TABLE_NAME",
        "LISTENER_API_URL": "https://listener-api-url/",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


def test_get_connection_ids(lambda_module):
    """
    Test get_connection_ids()
    """

    service_name = "ecommerce.test"
    connection_ids = [str(uuid.uuid4()) for _ in range(100)]

    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Items": [{
            "service": {"S": service_name},
            "id": {"S": connection_id}
        } for connection_id in connection_ids]
    }
    expected_params = {
        "TableName": "TABLE_NAME",
        "IndexName": "listener-service",
        "KeyConditionExpression": stub.ANY,
        "Limit": stub.ANY
    }
    table.add_response("query", response, expected_params)
    table.activate()

    retval = lambda_module.get_connection_ids(service_name)

    for connection_id in connection_ids:
        assert connection_id in retval

    table.assert_no_pending_responses()
    table.deactivate()


def test_send_event(lambda_module):
    """
    Test send_event()
    """

    event = {"message": "sample_payload"}
    event_bytes = json.dumps(event).encode("utf-8")
    connection_ids = [str(uuid.uuid4()) for _ in range(100)]

    apigw_mock = stub.Stubber(lambda_module.apigwmgmt)
    response = {}
    for connection_id in connection_ids:
        expected_params = {
            "ConnectionId": connection_id,
            "Data": event_bytes
        }
        apigw_mock.add_response("post_to_connection", response, expected_params)
    apigw_mock.activate()

    lambda_module.send_event(event, connection_ids)

    apigw_mock.assert_no_pending_responses()
    apigw_mock.deactivate()


def test_handler(monkeypatch, lambda_module, context):
    """
    Test handler()
    """

    service_name = "ecommerce.test"
    event = {
        "source": service_name,
        "message": "test_event"
    }
    connection_ids = [str(uuid.uuid4()) for _ in range(100)]

    called = {
        "get_connection_ids": False,
        "send_event": False
    }

    def get_connection_ids(service_name_got: str) -> List[str]:
        assert service_name == service_name
        called["get_connection_ids"] = True
        return connection_ids

    def send_event(event_got: dict, connection_ids_got: list):
        assert event == event_got
        assert connection_ids == connection_ids_got
        called["send_event"] = True

    monkeypatch.setattr(lambda_module, "get_connection_ids", get_connection_ids)
    monkeypatch.setattr(lambda_module, "send_event", send_event)

    lambda_module.handler(event, context)

    for k in called.keys():
        assert called[k] == True