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


@pytest.fixture
def main():
    return importlib.import_module("main")


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


def test_message_string(main):
    """
    Test message() with a string as input
    """

    msg = "This is a test"
    retval = main.message(msg)

    assert retval["body"] == json.dumps({"message": msg})
    assert retval["statusCode"] == 200

def test_message_dict(main):
    """
    Test message() with a dict as input
    """

    obj = {"key": "value"}
    retval = main.message(obj)

    assert retval["body"] == json.dumps(obj)
    assert retval["statusCode"] == 200

def test_message_status(main):
    """
    Test message() with a different status code
    """

    status_code = 400
    retval = main.message("Message", status_code)
    assert retval["statusCode"] == status_code


def test_compare_product_correct(main, product):
    """
    Compare a product that matches the DynamoDB item
    """

    retval = main.compare_product(product, product)

    assert retval is None


def test_compare_product_wrong_package(main, product):
    user_product = copy.deepcopy(product)
    user_product["package"]["weight"] += 100

    retval = main.compare_product(user_product, product)

    assert retval is not None
    assert retval[0] == product
    assert isinstance(retval[1], str)
    assert retval[1].find(product["productId"]) != -1


def test_compare_product_wrong_price(main, product):
    user_product = copy.deepcopy(product)
    user_product["price"] += 100

    retval = main.compare_product(user_product, product)

    assert retval is not None
    assert retval[0] == product
    assert isinstance(retval[1], str)
    assert retval[1].find(product["productId"]) != -1


def test_compare_product_missing(main, product):
    retval = main.compare_product(product, None)

    assert retval is not None
    assert retval[0] == product
    assert isinstance(retval[1], str)
    assert retval[1].find(product["productId"]) != -1