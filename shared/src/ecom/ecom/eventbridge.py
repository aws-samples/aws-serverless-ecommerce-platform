"""
EventBridge helpers for Lambda functions
"""


from datetime import datetime
import json
from boto3.dynamodb.types import TypeDeserializer
from .helpers import Encoder


__all__ = ["ddb_to_event"]


def ddb_to_event(
        ddb_record: dict,
        event_bus_name: str,
        source: str,
        object_type: str,
        resource_key: str
    ) -> dict:
    """
    Transforms a DynamoDB Streams record into an EventBridge event

    For this function to works, you need to have a StreamViewType of
    NEW_AND_OLD_IMAGES.
    """

    deserialize = TypeDeserializer().deserialize

    event = {
        "Time": datetime.now(),
        "Source": source,
        "Resources": [
            str(deserialize(ddb_record["dynamodb"]["Keys"][resource_key]))
        ],
        "EventBusName": event_bus_name
    }

    # Created event
    if ddb_record["eventName"].upper() == "INSERT":
        event["DetailType"] = "{}Created".format(object_type)
        event["Detail"] = json.dumps({
            k: deserialize(v)
            for k, v
            in ddb_record["dynamodb"]["NewImage"].items()
        }, cls=Encoder)

    # Deleted event
    elif ddb_record["eventName"].upper() == "REMOVE":
        event["DetailType"] = "{}Deleted".format(object_type)
        event["Detail"] = json.dumps({
            k: deserialize(v)
            for k, v
            in ddb_record["dynamodb"]["OldImage"].items()
        }, cls=Encoder)

    elif ddb_record["eventName"].upper() == "MODIFY":
        event["DetailType"] = "{}Modified".format(object_type)
        event["Detail"] = json.dumps({
            "new": {
                k: deserialize(v)
                for k, v
                in ddb_record["dynamodb"]["NewImage"].items()
            },
            "old": {
                k: deserialize(v)
                for k, v
                in ddb_record["dynamodb"]["OldImage"].items()
            }
        }, cls=Encoder)

    else:
        raise ValueError("Wrong eventName value for DynamoDB event: {}".format(ddb_record["eventName"]))

    return event