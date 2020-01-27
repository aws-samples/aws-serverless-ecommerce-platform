import copy
import json
import uuid
import pytest
from fixtures import context, lambda_module # pylint: disable=import-error
from helpers import mock_table # pylint: disable=import-error,no-name-in-module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "get_products",
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
def apigateway_event():
    """
    API Gateway Lambda Proxy event
    """
    return {
        "resource": "/",
        "path": "/",
        "httpMethod": "GET",
        "headers": {},
        "multiValueHeaders": {},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": {},
        "pathParameters": {},
        "stageVariables": {},
        "requestContext": {},
        "body": {},
        "isBase64Encoded": False
    }


def test_get_products(lambda_module, product):
    """
    Test get_products()
    """

    # Stub boto3
    table = mock_table(lambda_module.table, "scan", "productId", product)

    # Get products
    ddb_products, next_token = lambda_module.get_products()

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    assert ddb_products[0] == product
    assert next_token == None


def test_handler(lambda_module, apigateway_event, context, product):
    """
    Test handler()
    """

    # Stub boto3
    table = mock_table(lambda_module.table, "scan", "productId", product)

    # Get response
    response = lambda_module.handler(apigateway_event, context)

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "products" in body
    assert len(body["products"]) == 1
    assert body["products"][0] == product
    assert "nextToken" not in body


def test_handler_query_next_token(lambda_module, apigateway_event, context, product):
    """
    Test handler()
    """

    next_token = "NEXT_TOKEN"

    apigateway_event = copy.deepcopy(apigateway_event)
    apigateway_event["queryStringParameters"] = {"nextToken": next_token}

    # Stub boto3
    table = mock_table(
        lambda_module.table, "scan", "productId", product,
        expected_params={
            "TableName": lambda_module.table.name,
            "Limit": 20,
            "ExclusiveStartKey": {"productId": next_token}
        }
    )

    # Get response
    response = lambda_module.handler(apigateway_event, context)

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "products" in body
    assert len(body["products"]) == 1
    assert body["products"][0] == product
    assert "nextToken" not in body


def test_handler_response_next_token(lambda_module, apigateway_event, context, product):
    """
    Test handler()
    """

    next_token = "NEXT_TOKEN"

    # Stub boto3
    table = mock_table(
        lambda_module.table, "scan", "productId", product,
        response={
            "ConsumedCapacity": {},
            "LastEvaluatedKey": {"productId": {"S": next_token}}
        }
    )

    # Get response
    response = lambda_module.handler(apigateway_event, context)

    # Remove stub
    table.assert_no_pending_responses()
    table.deactivate()

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "products" in body
    assert len(body["products"]) == 1
    assert body["products"][0] == product
    assert "nextToken" in body
    assert body["nextToken"] == next_token