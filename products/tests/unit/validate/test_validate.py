import copy
import json
import uuid
import pytest
from fixtures import lambda_module


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "validate",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "TABLE_NAME": "TABLE_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)


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