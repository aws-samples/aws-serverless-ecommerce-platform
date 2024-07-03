import json
from boto3.dynamodb.types import TypeSerializer
from botocore import stub
import pytest
from fixtures import context, lambda_module, get_order, get_product # pylint: disable=import-error

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


@pytest.fixture
def order(get_order):
    return get_order()


def test_update_order(lambda_module):
    """
    test update_order()
    """

    order_id = "ORDER_ID"
    status = "STATUS"

    table = stub.Stubber(lambda_module.table.meta.client)
    expected_params = {
        "TableName": "TABLE_NAME",
        "Key": {"orderId": order_id},
        "UpdateExpression": stub.ANY,
        "ExpressionAttributeNames": {
            "#s": "status"
        },
        "ExpressionAttributeValues": {
            ":s": status
        }
    }
    table.add_response("update_item", {}, expected_params)
    table.activate()

    lambda_module.update_order(order_id, status)

    table.assert_no_pending_responses()
    table.deactivate()


def test_update_order_products(lambda_module, order):
    """
    test update_order() with products
    """

    order_id = "ORDER_ID"
    status = "STATUS"

    table = stub.Stubber(lambda_module.table.meta.client)
    # get_item stub
    expected_params = {
        "TableName": "TABLE_NAME",
        "Key": {"orderId": order_id},
        "AttributesToGet": ["products"]
    }
    response = {
        "Item": {
            k: TypeSerializer().serialize(v)
            for k, v in order.items()
        }
    }
    print(response)
    table.add_response("get_item", response, expected_params)
    # update_item stub
    expected_params = {
        "TableName": "TABLE_NAME",
        "Key": {"orderId": order_id},
        "UpdateExpression": stub.ANY,
        "ExpressionAttributeNames": {
            "#s": "status",
            "#p": "products"
        },
        "ExpressionAttributeValues": {
            ":p": order["products"],
            ":s": status
        }
    }
    table.add_response("update_item", {}, expected_params)
    table.activate()

    lambda_module.update_order(order_id, status, order["products"])

    table.assert_no_pending_responses()
    table.deactivate()


def test_handler(monkeypatch, lambda_module, context, order):
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
        "called": True,
        "products": True
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
        def update_order(order_id: str, status: str, products=None) -> None:
            assert test_case["called"]
            assert order_id == "ORDER_ID"
            assert status == test_case["status"]
            if test_case.get("products", False):
                assert products is not None
        monkeypatch.setattr(lambda_module, "update_order", update_order)

        event = {
            "resources": ["ORDER_ID"],
            "source": test_case["source"],
            "detail-type": test_case["detail-type"],
            "detail": order
        }
        lambda_module.handler(event, context)