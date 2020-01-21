import copy
import decimal
import json
import uuid
import pytest
from boto3.dynamodb.types import TypeSerializer
from botocore import stub
from fixtures import context, lambda_module


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


def test_decimal_encoder(lambda_module):
    """
    Test the JSON encoder
    """

    encoder = lambda_module.DecimalEncoder()

    assert isinstance(encoder.default(decimal.Decimal(10.5)), float)
    assert isinstance(encoder.default(decimal.Decimal(10)), int)


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


def test_validate_product_correct(lambda_module, product):
    """
    Test validate_product() against the right product
    """

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Item": {k: TypeSerializer().serialize(v) for k, v in product.items()}
    }
    expected_params = {
        "Key": {"productId": product["productId"]},
        "ProjectionExpression": stub.ANY,
        "ExpressionAttributeNames": stub.ANY,
        "TableName": lambda_module.TABLE_NAME
    }
    table.add_response("get_item", response, expected_params)
    table.activate()

    # Run command
    retval = lambda_module.validate_product(product)
    assert retval == None

    table.deactivate()


def test_validate_product_incorrect(lambda_module, product):
    """
    Test validate_product() against an incorrect product
    """

    product_incorrect = copy.deepcopy(product)
    product_incorrect["price"] += 200

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Item": {k: TypeSerializer().serialize(v) for k, v in product.items()}
    }
    expected_params = {
        "Key": {"productId": product["productId"]},
        "ProjectionExpression": stub.ANY,
        "ExpressionAttributeNames": stub.ANY,
        "TableName": lambda_module.TABLE_NAME
    }
    table.add_response("get_item", response, expected_params)
    table.activate()

    # Run command
    retval = lambda_module.validate_product(product_incorrect)
    assert retval is not None
    assert retval[0] == product
    assert isinstance(retval[1], str)

    table.deactivate()


def test_validate_products(lambda_module, product):
    """
    Test validate_products() against an incorrect product
    """

    product_incorrect = copy.deepcopy(product)
    product_incorrect["price"] += 200

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Item": {k: TypeSerializer().serialize(v) for k, v in product.items()}
    }
    expected_params = {
        "Key": {"productId": product["productId"]},
        "ProjectionExpression": stub.ANY,
        "ExpressionAttributeNames": stub.ANY,
        "TableName": lambda_module.TABLE_NAME
    }
    table.add_response("get_item", response, expected_params)
    table.activate()

    # Run command
    retval = lambda_module.validate_products([product_incorrect])
    assert len(retval) == 2
    assert len(retval[0]) == 1
    assert isinstance(retval[1], str)

    table.deactivate()


def test_handler_bad_body(lambda_module, context, product):
    """
    Test the function handler with a bad body
    """

    # Create request
    event = {
        "body": json.dumps({"products": [product]})+"{"
    }

    # Parse request
    response = lambda_module.handler(event, context)

    # Check response
    assert response["statusCode"] == 400

    # There should be a reason in the response body
    response_body = json.loads(response["body"])
    assert "message" in response_body
    assert isinstance(response_body["message"], str)


def test_handler_missing_products(lambda_module, context, product):
    """
    Test the function handler with missing 'products' in request body
    """

    # Create request
    event = {
        "body": json.dumps({})
    }

    # Parse request
    response = lambda_module.handler(event, context)

    # Check response
    assert response["statusCode"] == 400

    # There should be a reason in the response body
    response_body = json.loads(response["body"])
    assert "message" in response_body
    assert isinstance(response_body["message"], str)


def test_handler_incorrect(lambda_module, context, product):
    """
    Test the function handler against an incorrect product
    """

    product_incorrect = copy.deepcopy(product)
    product_incorrect["price"] += 200

    # Create request
    event = {
        "body": json.dumps({"products": [product_incorrect]})
    }

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Item": {k: TypeSerializer().serialize(v) for k, v in product.items()}
    }
    expected_params = {
        "Key": {"productId": product["productId"]},
        "ProjectionExpression": stub.ANY,
        "ExpressionAttributeNames": stub.ANY,
        "TableName": lambda_module.TABLE_NAME
    }
    table.add_response("get_item", response, expected_params)
    table.activate()

    # Parse request
    response = lambda_module.handler(event, context)

    # Remove stub
    table.deactivate()

    # Check response
    assert response["statusCode"] == 200

    # There should be 1 item in the response body
    response_body = json.loads(response["body"])
    assert "message" in response_body
    assert isinstance(response_body["message"], str)
    assert "products" in response_body
    assert len(response_body["products"]) == 1


def test_handler_correct(lambda_module, context, product):
    """
    Test the function handler against an incorrect product
    """

    # Create request
    event = {
        "body": json.dumps({"products": [product]})
    }

    # Stub boto3
    table = stub.Stubber(lambda_module.table.meta.client)
    response = {
        "Item": {k: TypeSerializer().serialize(v) for k, v in product.items()}
    }
    expected_params = {
        "Key": {"productId": product["productId"]},
        "ProjectionExpression": stub.ANY,
        "ExpressionAttributeNames": stub.ANY,
        "TableName": lambda_module.TABLE_NAME
    }
    table.add_response("get_item", response, expected_params)
    table.activate()

    # Parse request
    response = lambda_module.handler(event, context)

    # Remove stub
    table.deactivate()

    # Check response
    assert response["statusCode"] == 200

    # There should be 1 item in the response body
    response_body = json.loads(response["body"])
    assert "message" in response_body
    assert isinstance(response_body["message"], str)
    assert "products" not in response_body