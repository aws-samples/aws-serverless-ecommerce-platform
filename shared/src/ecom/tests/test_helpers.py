import datetime
import decimal
import json
from ecom import helpers # pylint: disable=import-error


def test_encoder(lambda_module):
    """
    Test the JSON encoder
    """

    encoder = lambda_module.Encoder()

    assert isinstance(encoder.default(decimal.Decimal(10.5)), float)
    assert isinstance(encoder.default(decimal.Decimal(10)), int)
    assert isinstance(encoder.default(datetime.datetime.now()), str)


def test_message_string():
    """
    Test message() with a string as input
    """

    msg = "This is a test"
    retval = helpers.message(msg)

    assert retval["body"] == json.dumps({"message": msg})
    assert retval["statusCode"] == 200


def test_message_dict():
    """
    Test message() with a dict as input
    """

    obj = {"key": "value"}
    retval = helpers.message(obj)

    assert retval["body"] == json.dumps(obj)
    assert retval["statusCode"] == 200


def test_message_status():
    """
    Test message() with a different status code
    """

    status_code = 400
    retval = helpers.message("Message", status_code)
    assert retval["statusCode"] == status_code