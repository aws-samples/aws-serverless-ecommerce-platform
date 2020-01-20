import copy
import importlib
import json
import os
import sys
import uuid
import pytest


FUNCTION_DIR = "validate"
MODULE_NAME = "main"
ENVIRON = {
    "ENVIRONMENT": "test",
    "TABLE_NAME": "TABLE_NAME",
    "POWERTOOLS_TRACE_DISABLED": "true"
}


@pytest.fixture(scope="module")
def lambda_module():
    """
    Main module of the Lambda function

    This also load environment variables and the path to the Lambda function
    prior to loading the module itself.
    """

    # Inject environment variables
    backup_environ = {}
    for key, value in ENVIRON.items():
        if key in os.environ:
            backup_environ[key] = os.environ[key]
        os.environ[key] = value

    # Add path for Lambda function
    sys.path.insert(0, os.path.join(os.environ["BUILD_DIR"], "src", FUNCTION_DIR))

    # Save the list of previously loaded modules
    prev_modules = list(sys.modules.keys())

    # Return the function module
    module = importlib.import_module(MODULE_NAME)
    yield module

    # Delete newly loaded modules
    new_keys = list(sys.modules.keys())
    for key in new_keys:
        if key not in prev_modules:
            del sys.modules[key]

    # Delete function module
    del module

    # Remove the Lambda function from path
    sys.path.pop(0)

    # Restore environment variables
    for key in ENVIRON.keys():
        if key in backup_environ:
            os.environ[key] = backup_environ[key]
        else:
            del os.environ[key]


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