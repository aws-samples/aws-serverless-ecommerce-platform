import importlib.machinery
import json
import os
import sys
import pytest



def setup_module(module):
    os.environ["ENVIRONMENT"] = "test"
    os.environ["TABLE_NAME"] = ""

    sys.path.insert(0, os.path.join(os.environ["BUILD_DIR"], "src", "validate"))

@pytest.fixture
def main():
    return importlib.import_module("main")


def test_message_string(main):
    msg = "This is a test"
    retval = main.message(msg)

    assert retval["body"] == json.dumps({"message": msg})
    assert retval["statusCode"] == 200

def test_message_dict(main):
    obj = {"key": "value"}
    retval = main.message(obj)

    assert retval["body"] == json.dumps(obj)
    assert retval["statusCode"] == 200

def test_message_status(main):
    status_code = 400
    retval = main.message("Message", status_code)
    assert retval["statusCode"] == status_code