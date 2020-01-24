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
    "function_dir": "get_orders",
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
def user_id():
    return str(uuid.uuid4())


@pytest.fixture
def next_token():
    return datetime.datetime.now().isoformat()


@pytest.fixture
def apigateway_event(next_token, user_id):
    """
    API Gateway Lambda Proxy event

    See https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
    """
    return {
        "resource": "/",
        "path": "/",
        "httpMethod": "GET",
        "headers": {},
        "multiValueHeaders": {},
        "queryStringParameters": {
            "nextToken": next_token
        },
        "multiValueQueryStringParameters": {},
        "pathParameters": {},
        "stageVariables": {},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": user_id,
                    "email": "john.doe@example.example"
                }
            }
        },
        "body": {},
        "isBase64Encoded": False
    }


@pytest.fixture
def order(user_id):
    """
    Single order
    """

    now = datetime.datetime.now()

    return {
        "orderId": str(uuid.uuid4()),
        "userId": user_id,
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


def test_encoder(lambda_module):
    """
    Test the JSON encoder
    """

    encoder = lambda_module.Encoder()

    assert isinstance(encoder.default(decimal.Decimal(10.5)), float)
    assert isinstance(encoder.default(decimal.Decimal(10)), int)
    assert isinstance(encoder.default(datetime.datetime.now()), str)


def test_message_string(lambda_module):
    """
    Test message() with a string as input
    """

    msg = "This is a test"
    retval = lambda_module.message(msg)

    assert retval["body"] == json.dumps({"message": msg})
    assert retval["statusCode"] == 200


def test_message_dict(lambda_module):
    """
    Test message() with a dict as input
    """

    obj = {"key": "value"}
    retval = lambda_module.message(obj)

    assert retval["body"] == json.dumps(obj)
    assert retval["statusCode"] == 200


def test_message_status(lambda_module):
    """
    Test message() with a different status code
    """

    status_code = 400
    retval = lambda_module.message("Message", status_code)
    assert retval["statusCode"] == status_code


def test_get_orders(lambda_module, user_id, next_token, order):
    """
    Test get_orders()
    """

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Items": [{k: TypeSerializer().serialize(v) for k, v in order.items()}],
        "Count": 1,
        "ScannedCount": 1,
        "LastEvaluatedKey": {
            "userId": {"S": order["userId"]},
            "createdDate": {"S": order["createdDate"]}
        },
        # We do not use ConsumedCapacity
        "ConsumedCapacity": {}
    }
    expected_params = {
        "TableName": lambda_module.TABLE_NAME,
        "IndexName": lambda_module.USER_INDEX_NAME,
        "Limit": lambda_module.ORDERS_LIMIT,
        # As the DynamoDB resource handles that, it might not return a
        # consistent value across versions.
        "KeyConditionExpression": stub.ANY,
        "Select": stub.ANY,
        "ExclusiveStartKey": {
            "userId": user_id,
            "createdDate": next_token
        }
    }
    table.add_response("query", response, expected_params)
    table.activate()

    # Gather orders
    orders, new_next_token = lambda_module.get_orders(user_id, next_token)

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    # Check response
    assert len(orders) == 1
    assert new_next_token is not None
    assert new_next_token == orders[-1]["createdDate"]
    compare_dict(order, orders[0])


def test_get_orders_no_next_token(lambda_module, user_id, order):
    """
    Test get_orders() withouth a next_token
    """

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Items": [{k: TypeSerializer().serialize(v) for k, v in order.items()}],
        "Count": 1,
        "ScannedCount": 1,
        "LastEvaluatedKey": {
            "userId": {"S": order["userId"]},
            "createdDate": {"S": order["createdDate"]}
        },
        # We do not use ConsumedCapacity
        "ConsumedCapacity": {}
    }
    expected_params = {
        "TableName": lambda_module.TABLE_NAME,
        "IndexName": lambda_module.USER_INDEX_NAME,
        "Limit": lambda_module.ORDERS_LIMIT,
        # As the DynamoDB resource handles that, it might not return a
        # consistent value across versions.
        "KeyConditionExpression": stub.ANY,
        "Select": stub.ANY
    }
    table.add_response("query", response, expected_params)
    table.activate()

    # Gather orders
    orders, new_next_token = lambda_module.get_orders(user_id, None)

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    # Check response
    assert len(orders) == 1
    assert new_next_token is not None
    assert new_next_token == orders[-1]["createdDate"]
    compare_dict(order, orders[0])



def test_handler(lambda_module, user_id, next_token, apigateway_event, order, context):
    """
    Test handler()
    """

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Items": [{k: TypeSerializer().serialize(v) for k, v in order.items()}],
        "Count": 1,
        "ScannedCount": 1,
        "LastEvaluatedKey": {
            "userId": {"S": order["userId"]},
            "createdDate": {"S": order["createdDate"]}
        },
        # We do not use ConsumedCapacity
        "ConsumedCapacity": {}
    }
    expected_params = {
        "TableName": lambda_module.TABLE_NAME,
        "IndexName": lambda_module.USER_INDEX_NAME,
        "Limit": lambda_module.ORDERS_LIMIT,
        # As the DynamoDB resource handles that, it might not return a
        # consistent value across versions.
        "KeyConditionExpression": stub.ANY,
        "Select": stub.ANY,
        "ExclusiveStartKey": {
            "userId": user_id,
            "createdDate": next_token
        }
    }
    table.add_response("query", response, expected_params)
    table.activate()

    # Send request
    response = lambda_module.handler(apigateway_event, context)

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    assert response["statusCode"] == 200
    assert "body" in response
    body = json.loads(response["body"])
    assert "orders" in body
    assert len(body["orders"]) == 1
    compare_dict(order, body["orders"][0])
    assert "nextToken" in body


def test_handler_forbidden(lambda_module, apigateway_event, context):
    """
    Test handler() without authorizer
    """

    del apigateway_event["requestContext"]["authorizer"]

    # Send request
    response = lambda_module.handler(apigateway_event, context)

    assert response["statusCode"] == 403
    assert "body" in response
    body = json.loads(response["body"])
    assert "message" in body