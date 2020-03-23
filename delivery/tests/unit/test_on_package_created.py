import copy
import datetime
import json
import random
import uuid
from botocore import stub
import pytest
import requests
import requests_mock
from fixtures import context, lambda_module, get_order, get_product # pylint: disable=import-error
from helpers import mock_table # pylint: disable=import-error,no-name-in-module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "on_package_created",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "ORDERS_API_URL": "mock://ORDERS_API_URL/",
        "TABLE_NAME": "TABLE_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


@pytest.fixture(scope="module")
def order(get_order):
    return get_order()


@pytest.fixture(scope="module")
def event(order):
    return {
        "version": "0",
        "id": str(uuid.uuid4()),
        "time": datetime.datetime.now(),
        "region": "eu-west-1",
        "account": "123456789012",
        "source": "ecommerce.warehouse",
        "detail-type": "PackageCreated",
        "resources": [order["orderId"]],
        "detail": order
    }


@pytest.fixture(scope="module")
def ddb_item(order):
    return {
        "orderId": order["orderId"],
        "isNew": "true",
        "status": "NEW",
        "address": order["address"]
    }


@pytest.fixture(scope="module")
def url(order):
    return "mock://ORDERS_API_URL/{}".format(order["orderId"])


def test_get_order(lambda_module, order, url):
    """
    Test get_order()
    """

    with requests_mock.Mocker() as m:
        m.get(url, text=json.dumps(order))
        response = lambda_module.get_order(order["orderId"])

    assert m.called
    assert m.call_count == 1
    assert m.request_history[0].method == "GET"
    assert m.request_history[0].url == url
    assert response == order


def test_get_order_empty(lambda_module, order, url):
    """
    Test get_order() with an empty response
    """

    with requests_mock.Mocker() as m:
        m.get(url, status_code=404, text=json.dumps({"message": "Order not found"}))
        response = lambda_module.get_order(order["orderId"])

    assert m.called
    assert m.call_count == 1
    assert m.request_history[0].method == "GET"
    assert m.request_history[0].url == url
    assert response is None


def test_save_shipping_request(lambda_module, order, ddb_item):
    """
    Test save_shipping_request()
    """

    table = mock_table(
        lambda_module.table, "get_item",
        ["orderId"]
    )
    table = mock_table(
        table, "put_item",
        ["orderId"],
        items=ddb_item,
        table_name=lambda_module.table.name
    )

    lambda_module.save_shipping_request(order)

    table.assert_no_pending_responses()
    table.deactivate()


def test_save_shipping_request_in_progress(lambda_module, order, ddb_item):
    """
    Test save_shipping_request() with an in progress shipping request
    """

    # Mock boto3
    ddb_item = copy.deepcopy(ddb_item)
    del ddb_item["isNew"]
    ddb_item["status"] = "IN_PROGRESS"
    table = mock_table(
        lambda_module.table, "get_item",
        ["orderId"],
        items=ddb_item
    )

    # Call
    lambda_module.save_shipping_request(order)

    # Assertions
    table.assert_no_pending_responses()
    table.deactivate()


def test_handler(lambda_module, event, context, order, url, ddb_item):
    """
    Test handler()
    """

    # Mock boto3
    table = mock_table(
        lambda_module.table, "get_item",
        ["orderId"]
    )
    table = mock_table(
        table, "put_item",
        ["orderId"],
        items=ddb_item,
        table_name=lambda_module.table.name
    )

    with requests_mock.Mocker() as m:
        # Mock requests
        m.get(url, text=json.dumps(order))
        lambda_module.handler(event, context)

    # Assertions
    assert m.called
    assert m.call_count == 1
    assert m.request_history[0].method == "GET"
    assert m.request_history[0].url == url

    table.assert_no_pending_responses()
    table.deactivate()


def test_handler_wrong_event_source(lambda_module, event, context):
    """
    Test handler() with an incorrect event
    """

    event = copy.deepcopy(event)
    event["source"] = "WRONG"

    with pytest.raises(AssertionError) as excinfo:
        lambda_module.handler(event, context)


def test_handler_wrong_event_detail_type(lambda_module, event, context):
    """
    Test handler() with an incorrect event
    """

    event = copy.deepcopy(event)
    event["detail-type"] = "WRONG"

    with pytest.raises(AssertionError) as excinfo:
        lambda_module.handler(event, context)

def test_handler_wrong_event_detail(lambda_module, event, context):
    """
    Test handler() with an incorrect event
    """

    event = copy.deepcopy(event)
    event["detail"] = {}

    with pytest.raises(KeyError) as excinfo:
        lambda_module.handler(event, context)


def test_handler_wrong_order(lambda_module, event, context, order, url):
    """
    Test handler() with a non-existing order
    """

    with requests_mock.Mocker() as m:
        m.get(url, status_code=404, text=json.dumps({"message": "Order not found"}))
        
        with pytest.raises(Exception, match="Failed to retrieve order .*") as excinfo:
            lambda_module.handler(event, context)

    assert m.called
    assert m.call_count == 1
    assert m.request_history[0].method == "GET"
    assert m.request_history[0].url == url