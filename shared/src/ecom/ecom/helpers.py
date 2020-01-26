"""
Helpers for Lambda functions
"""


from datetime import datetime, date
from decimal import Decimal
import json
from typing import Dict, Union
from boto3.dynamodb.types import TypeDeserializer


__all__ = ["Encoder", "message"]


class Encoder(json.JSONEncoder):
    """
    Helper class to convert a DynamoDB item to JSON
    """

    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, datetime) or isinstance(o, date):
            return o.isoformat()
        if isinstance(o, Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            return int(o)
        return super(Encoder, self).default(o)


def ddb_to_event(ddb_record: dict, event_bus_name: str, source: str,
                 object_type: str, resource_key: str) -> dict:
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


def message(msg: Union[dict, str], status_code: int = 200) -> Dict[str, Union[int, str]]:
    """
    Prepares a message for API Gateway
    """

    if isinstance(msg, str):
        msg = {"message": msg}

    return  {
        "statusCode": status_code,
        "body": json.dumps(msg, cls=Encoder)
    }