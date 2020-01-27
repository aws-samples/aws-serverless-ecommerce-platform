import copy
import decimal
import json
import uuid
import pytest
from boto3.dynamodb.types import TypeSerializer
from botocore import stub
from fixtures import context, lambda_module # pylint: disable=import-error


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "get_product",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "TABLE_NAME": "TABLE_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


@pytest.fixture
def product():
    return {
        "productId": str(uuid.uuid4()),
        "createdDate": "2020-01-27T16:54:21.999573",
        "modifiedDate": "2020-01-27T16:54:21.999573",
        "name": "Product name",
        "category": "Category",
        "tags": ["tag1", "tag2", "tag3"],
        "pictures": ["picture1", "picture2"],
        "package": {
            "width": 500,
            "length": 300,
            "height": 1000,
            "weight": 200
        },
        "price": 300
    }


@pytest.fixture
def apigateway_event(product):
    """
    API Gateway Lambda Proxy event
    """
    return {
        "resource": "/{productId}",
        "path": "/"+product["productId"],
        "httpMethod": "GET",
        "headers": {},
        "multiValueHeaders": {},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": {},
        "pathParameters": {
            "productId": product["productId"]
        },
        "stageVariables": {},
        "requestContext": {},
        "body": {},
        "isBase64Encoded": False
    }


def test_get_product(product, lambda_module):
    """
    Test get_product()
    """

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Item": {k: TypeSerializer().serialize(v) for k, v in product.items()},
        # We do not use ConsumedCapacity
        "ConsumedCapacity": {}
    }
    expected_params = {
        "TableName": lambda_module.TABLE_NAME,
        "Key": {"productId": product["productId"]}
    }
    table.add_response("get_item", response, expected_params)
    table.activate()

    # Get product
    ddb_product = lambda_module.get_product(product["productId"])

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    # Check response
    assert product == ddb_product


def test_get_product_empty(product, lambda_module):
    """
    Test get_product() with a non-existing product ID
    """

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "ConsumedCapacity": {}
    }
    expected_params = {
        "TableName": lambda_module.TABLE_NAME,
        "Key": {"productId": product["productId"]}
    }
    table.add_response("get_item", response, expected_params)
    table.activate()

    # Get product
    ddb_product = lambda_module.get_product(product["productId"])

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    # Check response
    assert ddb_product is None


def test_handler(product, apigateway_event, context, lambda_module):
    """
    Test handler()
    """

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Item": {k: TypeSerializer().serialize(v) for k, v in product.items()},
        # We do not use ConsumedCapacity
        "ConsumedCapacity": {}
    }
    expected_params = {
        "TableName": lambda_module.TABLE_NAME,
        "Key": {"productId": product["productId"]}
    }
    table.add_response("get_item", response, expected_params)
    table.activate()

    response = lambda_module.handler(apigateway_event, context)

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    # Check response
    assert response["statusCode"] == 200
    assert "body" in response
    body = json.loads(response["body"])
    assert body == product


def test_handler_no_param(apigateway_event, context, lambda_module):
    """
    Test handler() without a productId
    """

    apigateway_event = copy.deepcopy(apigateway_event)
    del apigateway_event["pathParameters"]

    response = lambda_module.handler(apigateway_event, context)

    # Check response
    assert response["statusCode"] == 400
    assert "body" in response
    body = json.loads(response["body"])
    assert "message" in body
    assert isinstance(body["message"], str)


def test_handler_missing(product, apigateway_event, context, lambda_module):
    """
    Test handler() with a missing product
    """

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        # We do not use ConsumedCapacity
        "ConsumedCapacity": {}
    }
    expected_params = {
        "TableName": lambda_module.TABLE_NAME,
        "Key": {"productId": product["productId"]}
    }
    table.add_response("get_item", response, expected_params)
    table.activate()

    response = lambda_module.handler(apigateway_event, context)

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    # Check response
    assert response["statusCode"] == 404
    assert "body" in response
    body = json.loads(response["body"])
    assert "message" in body
    assert isinstance(body["message"], str)