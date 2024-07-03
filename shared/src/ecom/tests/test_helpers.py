import datetime
import decimal
import json
import uuid
import pytest
from ecom import apigateway, eventbridge, helpers # pylint: disable=import-error


def test_encoder(lambda_module):
    """
    Test the JSON encoder
    """

    encoder = lambda_module.Encoder()

    assert isinstance(encoder.default(decimal.Decimal(10.5)), float)
    assert isinstance(encoder.default(decimal.Decimal(10)), int)
    assert isinstance(encoder.default(datetime.datetime.now()), str)


def test_ddb_to_event_insert():
    """
    Test ddb_to_event() with an INSERT record
    """

    event_bus_name = "EVENT_BUS_NAME"
    source = "SOURCE"
    object_type = "Object"
    resource_key = "pk"

    record = {
        "awsRegion": "eu-west-1",
        "dynamodb": {
            "Keys": {
                "pk": {"N": "123"},
                "sk": {"N": "456"}
            },
            "NewImage": {
                "SomeKey": {"S": "SomeValue"},
                "SomeOtherKey": {"N": "123456"}
            },
            "SequenceNumber": "1234567890123456789012345",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        },
        "eventID": str(uuid.uuid4()),
        "eventName": "INSERT",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1.0"
    }

    event = {
        "Source": source,
        "Resources": ["123"],
        "DetailType": "ObjectCreated",
        "Detail": {"SomeKey": "SomeValue", "SomeOtherKey": 123456},
        "EventBusName": event_bus_name
    }

    retval = eventbridge.ddb_to_event(record, event_bus_name, source, object_type, resource_key)

    for key, value in event.items():
        assert key in retval

        if key == "Detail":
            assert json.loads(value) == event[key]
        else:
            assert value == event[key]


def test_ddb_to_event_remove():
    """
    Test ddb_to_event() with a REMOVE record
    """

    event_bus_name = "EVENT_BUS_NAME"
    source = "SOURCE"
    object_type = "Object"
    resource_key = "pk"

    record = {
        "awsRegion": "eu-west-1",
        "dynamodb": {
            "Keys": {
                "pk": {"N": "123"},
                "sk": {"N": "456"}
            },
            "OldImage": {
                "SomeKey": {"S": "SomeValue"},
                "SomeOtherKey": {"N": "123456"}
            },
            "SequenceNumber": "1234567890123456789012345",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        },
        "eventID": str(uuid.uuid4()),
        "eventName": "REMOVE",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1.0"
    }

    event = {
        "Source": source,
        "Resources": ["123"],
        "DetailType": "ObjectDeleted",
        "Detail": {"SomeKey": "SomeValue", "SomeOtherKey": 123456},
        "EventBusName": event_bus_name
    }

    retval = eventbridge.ddb_to_event(record, event_bus_name, source, object_type, resource_key)

    for key, value in event.items():
        assert key in retval

        if key == "Detail":
            assert json.loads(value) == event[key]
        else:
            assert value == event[key]


def test_ddb_to_event_modify():
    """
    Test ddb_to_event() with a MODIFY record
    """

    event_bus_name = "EVENT_BUS_NAME"
    source = "SOURCE"
    object_type = "Object"
    resource_key = "pk"

    record = {
        "awsRegion": "eu-west-1",
        "dynamodb": {
            "Keys": {
                "pk": {"N": "123"},
                "sk": {"N": "456"}
            },
            "NewImage": {
                "SomeKey": {"S": "SomeValue"}
            },
            "OldImage": {
                "SomeOtherKey": {"N": "123456"}
            },
            "SequenceNumber": "1234567890123456789012345",
            "SizeBytes": 123,
            "StreamViewType": "NEW_AND_OLD_IMAGES"
        },
        "eventID": str(uuid.uuid4()),
        "eventName": "REMOVE",
        "eventSource": "aws:dynamodb",
        "eventVersion": "1.0"
    }

    event = {
        "Source": source,
        "Resources": ["123"],
        "DetailType": "ObjectModified",
        "Detail": {
            "new": {"SomeKey": "SomeValue"},
            "old": {"SomeOtherKey": 123456}
        },
        "EventBusName": event_bus_name
    }

    retval = eventbridge.ddb_to_event(record, event_bus_name, source, object_type, resource_key)

    for key, value in event.items():
        assert key in retval

        if key == "Detail":
            assert json.loads(value) == event[key]
        else:
            assert value == event[key]


def test_response_string():
    """
    Test response() with a string as input
    """

    msg = "This is a test"
    retval = apigateway.response(msg)

    assert retval["body"] == json.dumps({"message": msg})
    assert retval["statusCode"] == 200


def test_response_dict():
    """
    Test response() with a dict as input
    """

    obj = {"key": "value"}
    retval = apigateway.response(obj)

    assert retval["body"] == json.dumps(obj)
    assert retval["statusCode"] == 200


def test_response_status():
    """
    Test response() with a different status code
    """

    status_code = 400
    retval = apigateway.response("Message", status_code)
    assert retval["statusCode"] == status_code