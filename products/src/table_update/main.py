"""
TableUpdateFunction
"""


import datetime
import decimal
import json
import os
from typing import List, Optional
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context
import boto3
from boto3.dynamodb.types import TypeDeserializer


ENVIRONMENT = os.environ["ENVIRONMENT"]
EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]


eventbridge = boto3.client("events")
type_deserializer = TypeDeserializer()
logger = logger_setup()
tracer = Tracer()


class Encoder(json.JSONEncoder):
    """
    Helper class to convert a DynamoDB item to JSON
    """
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(Encoder, self).default(o)


@tracer.capture_method
def process_record(record: dict) -> Optional[dict]:
    """
    Process a single record from DynamoDB Stream
    """

    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.products",
        "Resources": [record["dynamodb"]["Keys"]["productId"]["S"]],
        "EventBusName": EVENT_BUS_NAME
    }

    # ProductCreated
    if record["eventName"].upper() == "INSERT":
        event["DetailType"] = "ProductCreated"
        event["Detail"] = json.dumps({
            k: type_deserializer.deserialize(v)
            for k, v
            in record["dynamodb"]["NewImage"].items()
        }, cls=Encoder)
    
    # ProductDeleted
    elif record["eventName"].upper() == "REMOVE": 
        event["DetailType"] = "ProductDeleted"
        event["Detail"] = json.dumps({
            k: type_deserializer.deserialize(v)
            for k, v
            in record["dynamodb"]["OldImage"].items()
        }, cls=Encoder)

    # ProductModified
    elif record["eventName"].upper() == "MODIFY":
        event["DetailType"] = "ProductModified"
        event["Detail"] = json.dumps({
            "new": {
                k: type_deserializer.deserialize(v)
                for k, v
                in record["dynamodb"]["NewImage"].items()
            },
            "old": {
                k: type_deserializer.deserialize(v)
                for k, v
                in record["dynamodb"]["OldImage"].items()
            }
        }, cls=Encoder)

    # Unknown action
    else:
        return

    return event


@tracer.capture_method
def send_events(events: List[dict]):
    logger.info("Sending {} events to EventBridge".format(len(events)))
    eventbridge.put_events(Entries=events)


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    """
    Lambda function handler for Products Table stream
    """

    logger.debug({
        "message": "Input event",
        "event": event
    })

    logger.debug({
        "message": "Records received",
        "records": event.get("Records", [])
    })

    events = [process_record(record) for record in event.get("Records", [])]

    logger.info("Received {} event(s)".format(len(events)))
    logger.debug({
        "message": "Events processed from records",
        "events": events
    })

    send_events(events)