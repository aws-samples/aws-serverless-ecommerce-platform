import copy
import importlib
import json
import os
import sys
import uuid
import pytest


def setup_module(module):
    os.environ["ENVIRONMENT"] = "test"
    os.environ["TABLE_NAME"] = ""
    os.environ["POWERTOOLS_TRACE_DISABLED"] = "true"

    sys.path.insert(0, os.path.join(os.environ["BUILD_DIR"], "src", "validate"))


def teardown_module(module):
    sys.path.pop(0)


@pytest.fixture
def validate():
    return importlib.import_module("validate")


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


def test_message_string(validate):
    """
    Test message() with a string as input
    """

    msg = "This is a test"
    retval = validate.message(msg)

    assert retval["body"] == json.dumps({"message": msg})
    assert retval["statusCode"] == 200

def test_message_dict(validate):
    """
    Test message() with a dict as input
    """

    obj = {"key": "value"}
    retval = validate.message(obj)

    assert retval["body"] == json.dumps(obj)
    assert retval["statusCode"] == 200

def test_message_status(validate):
    """
    Test message() with a different status code
    """

    status_code = 400
    retval = validate.message("Message", status_code)
    assert retval["statusCode"] == status_code


def test_compare_product_correct(validate, product):
    """
    Compare a product that matches the DynamoDB item
    """

    retval = validate.compare_product(product, product)

    assert retval is None


def test_compare_product_wrong_package(validate, product):
    user_product = copy.deepcopy(product)
    user_product["package"]["weight"] += 100

    retval = validate.compare_product(user_product, product)

    assert retval is not None
    assert retval[0] == product
    assert isinstance(retval[1], str)
    assert retval[1].find(product["productId"]) != -1


def test_compare_product_wrong_price(validate, product):
    user_product = copy.deepcopy(product)
    user_product["price"] += 100

    retval = validate.compare_product(user_product, product)

    assert retval is not None
    assert retval[0] == product
    assert isinstance(retval[1], str)
    assert retval[1].find(product["productId"]) != -1


def test_compare_product_missing(validate, product):
    retval = validate.compare_product(product, None)

    assert retval is not None
    assert retval[0] == product
    assert isinstance(retval[1], str)
    assert retval[1].find(product["productId"]) != -1