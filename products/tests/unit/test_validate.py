import copy
import decimal
import json
import uuid
import pytest
from boto3.dynamodb.types import TypeSerializer
from botocore import stub
from fixtures import apigateway_event, context, lambda_module # pylint: disable=import-error


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "validate",
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
        "name": "Product name",
        "package": {
            "width": 500,
            "length": 300,
            "height": 1000,
            "weight": 200
        },
        "price": 300
    }


def test_compare_product_correct(lambda_module, product):
    """
    Compare a product that matches the DynamoDB item
    """

    retval = lambda_module.compare_product(product, product)

    assert retval is None


def test_compare_product_wrong_package(lambda_module, product):
    user_product = copy.deepcopy(product)
    user_product["package"]["weight"] += 100

    retval = lambda_module.compare_product(user_product, product)

    assert retval is not None
    assert retval[0] == product
    assert isinstance(retval[1], str)
    assert retval[1].find(product["productId"]) != -1


def test_compare_product_wrong_price(lambda_module, product):
    user_product = copy.deepcopy(product)
    user_product["price"] += 100

    retval = lambda_module.compare_product(user_product, product)

    assert retval is not None
    assert retval[0] == product
    assert isinstance(retval[1], str)
    assert retval[1].find(product["productId"]) != -1


def test_compare_product_missing(lambda_module, product):
    retval = lambda_module.compare_product(product, None)

    assert retval is not None
    assert retval[0] == product
    assert isinstance(retval[1], str)
    assert retval[1].find(product["productId"]) != -1


def test_validate_products(lambda_module, product):
    """
    Test validate_products() against a correct product
    """


    # Stub boto3
    dynamodb = stub.Stubber(lambda_module.dynamodb)
    response = {
        "Responses": {
            lambda_module.TABLE_NAME: [{k: TypeSerializer().serialize(v) for k, v in product.items()}]
        }
    }
    expected_params = {
        "RequestItems": {
            lambda_module.TABLE_NAME: {
                "Keys": [{"productId": {"S": product["productId"]}}],
                "ProjectionExpression": stub.ANY,
                "ExpressionAttributeNames": stub.ANY
            }
        }
    }
    dynamodb.add_response("batch_get_item", response, expected_params)
    dynamodb.activate()

    # Run command
    retval = lambda_module.validate_products([product])
    print(retval)
    assert len(retval) == 2
    assert len(retval[0]) == 0
    assert isinstance(retval[1], str)

    dynamodb.deactivate()


def test_validate_products_multiple(lambda_module, product):
    """
    Test validate_products() with multiple DynamoDB calls
    """

    products = []
    for i in range(0, 105):
        product_temp = copy.deepcopy(product)
        product_temp["productId"] += str(i)
        products.append(product_temp)

    # Stub boto3
    dynamodb = stub.Stubber(lambda_module.dynamodb)
    response = {
        "Responses": {
            lambda_module.TABLE_NAME: [{k: TypeSerializer().serialize(v) for k, v in p.items()} for p in products[0:100]]
        }
    }
    expected_params = {
        "RequestItems": {
            lambda_module.TABLE_NAME: {
                "Keys": [{"productId": {"S": p["productId"]}} for p in products[0:100]],
                "ProjectionExpression": stub.ANY,
                "ExpressionAttributeNames": stub.ANY
            }
        }
    }
    dynamodb.add_response("batch_get_item", response, expected_params)
    response = {
        "Responses": {
            lambda_module.TABLE_NAME: [{k: TypeSerializer().serialize(v) for k, v in p.items()} for p in products[100:]]
        }
    }
    expected_params = {
        "RequestItems": {
            lambda_module.TABLE_NAME: {
                "Keys": [{"productId": {"S": p["productId"]}} for p in products[100:]],
                "ProjectionExpression": stub.ANY,
                "ExpressionAttributeNames": stub.ANY
            }
        }
    }
    dynamodb.add_response("batch_get_item", response, expected_params)
    dynamodb.activate()

    # Run command
    retval = lambda_module.validate_products(products)
    print(retval)
    assert len(retval) == 2
    assert len(retval[0]) == 0
    assert isinstance(retval[1], str)

    dynamodb.deactivate()


def test_validate_products_paginated(lambda_module, product):
    """
    Test validate_products() with pagination
    """


    # Stub boto3
    dynamodb = stub.Stubber(lambda_module.dynamodb)
    response = {
        "Responses": {
            lambda_module.TABLE_NAME: [{k: TypeSerializer().serialize(v) for k, v in product.items()}]
        },
        "UnprocessedKeys": {
            lambda_module.TABLE_NAME: {
                "Keys": [{"productId": {"S": product["productId"]}}],
                "ProjectionExpression": "#productId, #name, #package, #price",
                "ExpressionAttributeNames": {
                    "#productId": "productId",
                    "#name": "name",
                    "#package": "package",
                    "#price": "price"
                }
            }
        }
    }
    expected_params = {
        "RequestItems": {
            lambda_module.TABLE_NAME: {
                "Keys": [{"productId": {"S": product["productId"]}}],
                "ProjectionExpression": stub.ANY,
                "ExpressionAttributeNames": stub.ANY
            }
        }
    }
    dynamodb.add_response("batch_get_item", response, expected_params)

    # Stub a second answer
    response = {
        "Responses": {
            lambda_module.TABLE_NAME: [{k: TypeSerializer().serialize(v) for k, v in product.items()}]
        }
    }
    expected_params = {
        "RequestItems": {
            lambda_module.TABLE_NAME: {
                "Keys": [{"productId": {"S": product["productId"]}}],
                "ProjectionExpression": stub.ANY,
                "ExpressionAttributeNames": stub.ANY
            }
        }
    }
    dynamodb.add_response("batch_get_item", response, expected_params)
    dynamodb.activate()

    # Run command
    retval = lambda_module.validate_products([product])
    print(retval)
    assert len(retval) == 2
    assert len(retval[0]) == 0
    assert isinstance(retval[1], str)

    dynamodb.deactivate()


def test_validate_products_incorrect(lambda_module, product):
    """
    Test validate_products() against an incorrect product
    """

    product_incorrect = copy.deepcopy(product)
    product_incorrect["price"] += 200

    # Stub boto3
    dynamodb = stub.Stubber(lambda_module.dynamodb)
    response = {
        "Responses": {
            lambda_module.TABLE_NAME: [{k: TypeSerializer().serialize(v) for k, v in product.items()}]
        }
    }
    expected_params = {
        "RequestItems": {
            lambda_module.TABLE_NAME: {
                "Keys": [{"productId": {"S": product["productId"]}}],
                "ProjectionExpression": stub.ANY,
                "ExpressionAttributeNames": stub.ANY
            }
        }
    }
    dynamodb.add_response("batch_get_item", response, expected_params)
    dynamodb.activate()

    # Run command
    retval = lambda_module.validate_products([product_incorrect])
    print(retval)
    assert len(retval) == 2
    assert len(retval[0]) == 1
    assert isinstance(retval[1], str)

    dynamodb.deactivate()


def test_handler_bad_body(monkeypatch, lambda_module, apigateway_event, context, product):
    """
    Test the function handler with a bad body
    """

    def validate_products(products):
        assert False # This should never be called

    monkeypatch.setattr(lambda_module, "validate_products", validate_products)

    # Create request
    event = apigateway_event(
        iam="USER_ARN",
        body=json.dumps({"products": [product]})+"{"
    )

    # Parse request
    response = lambda_module.handler(event, context)

    # Check response
    assert response["statusCode"] == 400

    # There should be a reason in the response body
    response_body = json.loads(response["body"])
    assert "message" in response_body
    assert isinstance(response_body["message"], str)


def test_handler_missing_products(monkeypatch, lambda_module, apigateway_event, context, product):
    """
    Test the function handler with missing 'products' in request body
    """

    def validate_products(products):
        assert False # This should never be called

    monkeypatch.setattr(lambda_module, "validate_products", validate_products)

    # Create request
    event = apigateway_event(
        iam="USER_ARN",
        body=json.dumps({})
    )

    # Parse request
    response = lambda_module.handler(event, context)

    # Check response
    assert response["statusCode"] == 400

    # There should be a reason in the response body
    response_body = json.loads(response["body"])
    assert "message" in response_body
    assert isinstance(response_body["message"], str)


def test_handler_incorrect(monkeypatch, lambda_module, apigateway_event, context, product):
    """
    Test the function handler against an incorrect product
    """

    def validate_products(products):
        return [product], "Invalid product."

    monkeypatch.setattr(lambda_module, "validate_products", validate_products)

    product_incorrect = copy.deepcopy(product)
    product_incorrect["price"] += 200

    # Create request
    event = apigateway_event(
        iam="USER_ARN",
        body=json.dumps({"products": [product_incorrect]})
    )

    # Parse request
    response = lambda_module.handler(event, context)

    # Check response
    assert response["statusCode"] == 200

    # There should be 1 item in the response body
    response_body = json.loads(response["body"])
    assert "message" in response_body
    assert isinstance(response_body["message"], str)
    assert "products" in response_body
    assert len(response_body["products"]) == 1


def test_handler_correct(monkeypatch, lambda_module, apigateway_event, context, product):
    """
    Test the function handler against an incorrect product
    """

    def validate_products(products):
        return [], ""

    monkeypatch.setattr(lambda_module, "validate_products", validate_products)

    # Create request
    event = apigateway_event(
        iam="USER_ARN",
        body=json.dumps({"products": [product]})
    )

    # Parse request
    response = lambda_module.handler(event, context)

    # Check response
    assert response["statusCode"] == 200

    # There should be 1 item in the response body
    response_body = json.loads(response["body"])
    assert "message" in response_body
    assert isinstance(response_body["message"], str)
    assert "products" not in response_body