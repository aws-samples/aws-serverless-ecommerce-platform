import copy
import datetime
import decimal
import json
import uuid
import pytest
from boto3.dynamodb.types import TypeSerializer
from botocore import stub
from fixtures import context, lambda_module # pylint: disable=import-error
from helpers import compare_dict # pylint: disable=import-error,no-name-in-module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "get_order",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "TABLE_NAME": "TABLE_NAME",
        "USER_INDEX_NAME": "USER_INDEX_NAME",
        "ORDERS_LIMIT": "20",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


@pytest.fixture
def apigateway_event(order):
    """
    API Gateway Lambda Proxy event

    See https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
    """
    return {
        "resource": "/backend/{orderId}",
        "path": "/backend/"+order["orderId"],
        "httpMethod": "GET",
        "headers": {},
        "multiValueHeaders": {},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": {},
        "pathParameters": {
            "orderId": order["orderId"]
        },
        "stageVariables": {},
        "requestContext": {
            "identity": {
                "accountId": "123456789012",
                "caller": "CALLER",
                "sourceIp": "127.0.0.1",
                "accessKey": "ACCESS_KEY",
                "userArn": "arn:aws:iam::123456789012:user/alice",
                "userAgent": "PostmanRuntime/7.1.1",
                "user": "CALLER"
            }
        },
        "body": {},
        "isBase64Encoded": False
    }


@pytest.fixture
def order():
    """
    Single order
    """

    now = datetime.datetime.now()

    return {
        "orderId": str(uuid.uuid4()),
        "userId": str(uuid.uuid4()),
        "createdDate": now.isoformat(),
        "modifiedDate": now.isoformat(),
        "status": "NEW",
        "products": [{
            "productId": str(uuid.uuid4()),
            "name": "Test Product",
            "package": {
                "width": 1000,
                "length": 900,
                "height": 800,
                "weight": 700
            },
            "price": 300,
            "quantity": 4
        }],
        "address": {
            "name": "John Doe",
            "companyName": "Company Inc.",
            "streetAddress": "123 Street St",
            "postCode": "12345",
            "city": "Town",
            "state": "State",
            "country": "SE",
            "phoneNumber": "+123456789"
        },
        "deliveryPrice": 200,
        "total": 1400
    }


def test_get_order(lambda_module, order):
    """
    Test get_order()
    """

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Item": {k: TypeSerializer().serialize(v) for k, v in order.items()},
        # We do not use ConsumedCapacity
        "ConsumedCapacity": {}
    }
    expected_params = {
        "TableName": lambda_module.TABLE_NAME,
        "Key": {"orderId": order["orderId"]}
    }
    table.add_response("get_item", response, expected_params)
    table.activate()

    # Gather orders
    ddb_order = lambda_module.get_order(order["orderId"])

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    # Check response
    compare_dict(order, ddb_order)


def test_handler(lambda_module, apigateway_event, order, context):
    """
    Test handler()
    """

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Item": {k: TypeSerializer().serialize(v) for k, v in order.items()},
        # We do not use ConsumedCapacity
        "ConsumedCapacity": {}
    }
    expected_params = {
        "TableName": lambda_module.TABLE_NAME,
        "Key": {"orderId": order["orderId"]}
    }
    table.add_response("get_item", response, expected_params)
    table.activate()

    # Send request
    response = lambda_module.handler(apigateway_event, context)

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    assert response["statusCode"] == 200
    assert "body" in response
    body = json.loads(response["body"])
    compare_dict(order, body)


def test_handler_not_found(lambda_module, apigateway_event, order, context):
    """
    Test handler() with an unknown order ID
    """

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        # We do not use ConsumedCapacity
        "ConsumedCapacity": {}
    }
    expected_params = {
        "TableName": lambda_module.TABLE_NAME,
        "Key": {"orderId": order["orderId"]}
    }
    table.add_response("get_item", response, expected_params)
    table.activate()

    # Send request
    response = lambda_module.handler(apigateway_event, context)

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    assert response["statusCode"] == 404
    assert "body" in response
    body = json.loads(response["body"])
    assert "message" in body
    assert isinstance(body["message"], str)


def test_handler_forbidden(lambda_module, apigateway_event, context):
    """
    Test handler() without claims
    """

    apigateway_event = copy.deepcopy(apigateway_event)
    del apigateway_event["requestContext"]["identity"]

    # Send request
    response = lambda_module.handler(apigateway_event, context)

    assert response["statusCode"] == 401
    assert "body" in response
    body = json.loads(response["body"])
    assert "message" in body
    assert isinstance(body["message"], str)


def test_handler_missing_order(lambda_module, apigateway_event, context):
    """
    Test handler() without orderId
    """

    apigateway_event = copy.deepcopy(apigateway_event)
    apigateway_event["pathParameters"] = None

    # Send request
    response = lambda_module.handler(apigateway_event, context)

    assert response["statusCode"] == 400
    assert "body" in response
    body = json.loads(response["body"])
    assert "message" in body
    assert isinstance(body["message"], str)