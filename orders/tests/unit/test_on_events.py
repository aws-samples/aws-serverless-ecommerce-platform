from boto3.dynamodb.types import TypeSerializer
from botocore import stub
import pytest
from fixtures import context, lambda_module # pylint: disable=import-error

lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "on_events",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "TABLE_NAME": "TABLE_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


def test_set_status(lambda_module):
    """
    test set_status()
    """

    order_id = "ORDER_ID"
    status = "STATUS"

    table = stub.Stubber(lambda_module.table.meta.client)
    expected_params = {
        "TableName": "TABLE_NAME",
        "Key": {"orderId": order_id},
        "UpdateExpression": stub.ANY,
        "ExpressionAttributeNames": stub.ANY,
        "ExpressionAttributeValues": {
            ":s": status
        }
    }
    table.add_response("update_item", {}, expected_params)
    table.activate()

    lambda_module.set_status(order_id, status)

    table.assert_no_pending_responses()
    table.deactivate()


def test_handler_fulfilled(monkeypatch, lambda_module, context):
    """
    Test handler()
    """

    test_cases = [{
        "status": "FULFILLED",
        "source": "ecommerce.delivery",
        "detail-type": "DeliveryCompleted",
        "called": True
    }, {
        "status": "DELIVERY_FAILED",
        "source": "ecommerce.delivery",
        "detail-type": "DeliveryFailed",
        "called": True
    }, {
        "status": "PACKAGED",
        "source": "ecommerce.warehouse",
        "detail-type": "PackageCreated",
        "called": True
    }, {
        "status": "PACKAGING_FAILED",
        "source": "ecommerce.warehouse",
        "detail-type": "PackagingFailed",
        "called": True
    }, {
        "status": "UNKNOWN",
        "source": "ecommerce.warehouse",
        "detail-type": "UnknownDetailType",
        "called": False
    }, {
        "status": "UNKNOWN",
        "source": "ecommerce.delivery",
        "detail-type": "UnknownDetailType",
        "called": False
    }, {
        "status": "UNKNOWN",
        "source": "UNKNOWN",
        "detail-type": "UnknownDetailType",
        "called": False
    }]

    for test_case in test_cases:
        def set_status(order_id: str, status: str) -> None:
            assert test_case["called"]
            assert order_id == "ORDER_ID"
            assert status == test_case["status"]
        monkeypatch.setattr(lambda_module, "set_status", set_status)

        event = {
            "resources": ["ORDER_ID"],
            "source": test_case["source"],
            "detail-type": test_case["detail-type"]
        }
        lambda_module.handler(event, context)