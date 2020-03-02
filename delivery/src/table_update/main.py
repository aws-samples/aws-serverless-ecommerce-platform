"""
TableUpdateFunction
"""


import datetime
import json
import os
from typing import List, Optional
import boto3
from boto3.dynamodb.types import TypeDeserializer
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context
from ecom.helpers import Encoder


ENVIRONMENT = os.environ["ENVIRONMENT"]
EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]


eventbridge = boto3.client("events") # pylint: disable=invalid-name
deserialize = TypeDeserializer().deserialize # pylint: disable=invalid-name
logger = logger_setup() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def send_events(events: List[dict]):
    """
    Send events to EventBridge
    """

    logger.info("Sending %d events to EventBridge", len(events))
    eventbridge.put_events(Entries=events)


def process_record(record: dict) -> Optional[dict]:
    """
    Process record from DynamoDB

    A record have a 'status' field that can take any of the following values:
     - NEW
     - IN_PROGRESS
     - COMPLETED
     - FAILED
    """
    # pylint: disable=no-else-return

    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.delivery",
        "Resources": [
            deserialize(record["dynamodb"]["Keys"]["orderId"])
        ],
        "EventBusName": EVENT_BUS_NAME
    }
    if record["dynamodb"].get("OldImage", None) is not None:
        event["Detail"] = json.dumps({
            "orderId": deserialize(record["dynamodb"]["OldImage"]["orderId"]),
            "address": deserialize(record["dynamodb"]["OldImage"]["address"])
        }, cls=Encoder)
    else:
        event["Detail"] = json.dumps({
            "orderId": deserialize(record["dynamodb"]["NewImage"]["orderId"]),
            "address": deserialize(record["dynamodb"]["NewImage"]["address"])
        }, cls=Encoder)

    # INSERT records
    # These events are just discarded
    if record["eventName"].upper() == "INSERT":
        logger.debug({
            "message": "Ignoring INSERT record",
            "record": record
        })
        return None

    # REMOVE records
    elif record["eventName"].upper() == "REMOVE":
        if deserialize(record["dynamodb"]["OldImage"]["status"]) in ["COMPLETED", "FAILED"]:
            logger.debug({
                "message": "Ignoring REMOVE of completed record",
                "record": record
            })
            return None

        logger.warning({
            "message": "Failed delivery: REMOVE before completion",
            "record": record
        })
        event["DetailType"] = "DeliveryFailed"
        return event

    # MODIFY records
    elif record["eventName"].upper() == "MODIFY":
        if deserialize(record["dynamodb"]["NewImage"]["status"]) == "FAILED":
            logger.warning({
                "message": "Failed delivery: status marked as FAILED",
                "record": record
            })
            event["DetailType"] = "DeliveryFailed"
            return event

        elif deserialize(record["dynamodb"]["NewImage"]["status"]) == "COMPLETED":
            logger.info({
                "message": "Delivery completed",
                "record": record
            })
            event["DetailType"] = "DeliveryCompleted"
            return event

        else:
            return None

    else:
        raise ValueError("Wrong eventName value for DynamoDB event: {}".format(record["eventName"]))


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler for Orders Table stream
    """

    logger.debug({
        "message": "Input event",
        "event": event
    })

    logger.debug({
        "message": "Records received",
        "records": event.get("Records", [])
    })

    events = [
        process_record(record)
        for record in event.get("Records", [])
    ]
    events = [event for event in events if event is not None]    

    logger.info("Received %d event(s)", len(events))
    logger.debug({
        "message": "Events processed from records",
        "events": events
    })

    if len(events) > 0:
        send_events(events)
