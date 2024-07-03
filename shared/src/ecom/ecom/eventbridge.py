"""
EventBridge helpers for Lambda functions
"""


from datetime import datetime
import json
import os
from boto3.dynamodb.types import TypeDeserializer
from .helpers import Encoder


__all__ = ["ddb_to_event"]
deserialize = TypeDeserializer().deserialize


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

    event = {
        "Time": datetime.now(),
        "Source": source,
        "Resources": [
            str(deserialize(ddb_record["dynamodb"]["Keys"][resource_key]))
        ],
        "EventBusName": event_bus_name
    }

    # Inject X-Ray trace ID
    trace_id = os.environ.get("_X_AMZN_TRACE_ID", None)
    if trace_id:
        event["TraceHeader"] = trace_id

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
        new = {
            k: deserialize(v)
            for k, v
            in ddb_record["dynamodb"]["NewImage"].items()
        }
        old = {
            k: deserialize(v)
            for k, v
            in ddb_record["dynamodb"]["OldImage"].items()
        }

        # Old keys not in NewImage
        changed = [k for k in old.keys() if k not in new.keys()]
        for k in new.keys():
            # New keys not in OldImage
            if k not in old.keys():
                changed.append(k)
            # New keys that are not equal to old values
            elif new[k] != old[k]:
                changed.append(k)

        event["DetailType"] = "{}Modified".format(object_type)
        event["Detail"] = json.dumps({
            "new": new,
            "old": old,
            "changed": changed
        }, cls=Encoder)

    else:
        raise ValueError("Wrong eventName value for DynamoDB event: {}".format(ddb_record["eventName"]))

    return event