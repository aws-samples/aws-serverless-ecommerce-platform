"""
TableUpdateFunction
"""


import os
from typing import List
import boto3
from boto3.dynamodb.types import TypeDeserializer
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging.logger import Logger
from ecom.eventbridge import ddb_to_event # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]


eventbridge = boto3.client("events") # pylint: disable=invalid-name
type_deserializer = TypeDeserializer() # pylint: disable=invalid-name
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def send_events(events: List[dict]):
    """
    Send events to EventBridge
    """

    logger.info("Sending %d events to EventBridge", len(events))
    # EventBridge only supports batches of up to 10 events
    for i in range(0, len(events), 10):
        eventbridge.put_events(Entries=events[i:i+10])


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
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

    events = [
        ddb_to_event(record, EVENT_BUS_NAME, "ecommerce.products", "Product", "productId")
        for record in event.get("Records", [])
    ]

    logger.info("Received %d event(s)", len(events))
    logger.debug({
        "message": "Events processed from records",
        "events": events
    })

    send_events(events)
