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
        event["Detail"] = {
            k: type_deserializer.deserialize(v)
            for k, v
            in record["dynamodb"]["NewImage"].items()
        }
    
    # ProductDeleted
    elif record["eventName"].upper() == "REMOVE": 
        event["DetailType"] = "ProductDeleted"
        event["Detail"] = {
            k: type_deserializer.deserialize(v)
            for k, v
            in record["dynamodb"]["OldImage"].items()
        }

    # ProductModified
    elif record["eventName"].upper() == "MODIFY":
        event["DetailType"] = "ProductModified"
        event["Detail"] = {
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
        }

    # Unknown action
    else:
        return

    return event


@tracer.capture_method
def send_events(events: List[dict]):
    eventbridge.put_events(Entires=events)


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    """
    Lambda function handler for Products Table stream
    """

    events = [process_record(record) for record in event.get("Records", [])]

    send_events(events)