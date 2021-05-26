"""
TableUpdateFunction
"""


import datetime
import json
import os
import warnings
from typing import List, Optional
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging.logger import Logger
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit
import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeDeserializer
from ecom.helpers import Encoder #pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]
METADATA_KEY = os.environ["METADATA_KEY"]
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
eventbridge = boto3.client("events") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
type_deserializer = TypeDeserializer() # pylint: disable=invalid-name
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name
metrics = Metrics(namespace="ecommerce.warehouse", service="warehouse")


event_type_to_metric = {
    'PackageCreated':'packageCreated',
    'PackagingFailed':'packagingFailed'
}


@tracer.capture_method
def send_events(events: List[dict]):
    """
    Send events to EventBridge
    """

    logger.info("Sending %d events to EventBridge", len(events))
    # EventBridge only supports batches of up to 10 events
    for i in range(0, len(events), 10):
        eventbridge.put_events(Entries=events[i:i+10])


@tracer.capture_method
def parse_record(ddb_record: dict) -> Optional[dict]:
    """
    Parse a DynamoDB record into an EventBridge event
    """

    # Discard records that concern removed events, non-metadata items or items that are
    # not in the COMPLETED status.
    if (ddb_record["eventName"].upper() == "REMOVE"
            or ddb_record["dynamodb"]["NewImage"]["productId"]["S"] != METADATA_KEY
            or ddb_record["dynamodb"]["NewImage"]["status"]["S"] != "COMPLETED"):
        return None

    # Gather information
    order_id = ddb_record["dynamodb"]["NewImage"]["orderId"]["S"]
    products = get_products(order_id)

    # Create the detail
    detail_type = "PackagingFailed"
    detail = {
        "orderId": order_id
    }
    # If there are products, we successfully created a package
    if len(products) > 0:
        detail_type = "PackageCreated"
        detail["products"] = products

    metrics.add_metric(name=event_type_to_metric[detail_type], unit=MetricUnit.Count, value=1)

    # Return event
    return {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.warehouse",
        "Resources": [order_id],
        "EventBusName": EVENT_BUS_NAME,
        "DetailType": detail_type,
        "Detail": json.dumps(detail, cls=Encoder)
    }

@tracer.capture_method
def get_products(order_id: str) -> List[dict]:
    """
    Retrieve products from the DynamoDB table
    """

    res = table.query(
        KeyConditionExpression=Key("orderId").eq(order_id),
        Limit=100
    )
    logger.info({
        "message": "Retrieving {} products from order {}".format(
            len(res.get("Items", [])), order_id
        ),
        "operation": "query",
        "orderId": order_id
    })
    products = res.get("Items", [])

    while res.get("LastEvaluatedKey", None) is not None:
        res = table.query(
            KeyConditionExpression=Key("orderId").eq(order_id),
            ExclusiveStartKey=res["LastEvaluatedKey"],
            Limit=100
        )
        logger.info({
            "message": "Retrieving {} products from order {}".format(
                len(res.get("Items", [])), order_id
            ),
            "operation": "query",
            "orderId": order_id
        })
        products.extend(res.get("Items", []))

    return products


@metrics.log_metrics
@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler for Warehouse Table stream
    """

    # this handler may complete without publishing any metrics
    warnings.filterwarnings("ignore", "No metrics to publish*")

    metrics.add_dimension(name="environment", value=ENVIRONMENT)

    logger.debug({
        "message": "Input event",
        "event": event
    })

    logger.debug({
        "message": "Records received",
        "records": event.get("Records", [])
    })

    # Parse events
    events = [
        parse_record(record)
        for record in event.get("Records", [])
    ]

    # Filter None events
    events = [event for event in events if event is not None]

    logger.info("Received %d event(s)", len(events))
    logger.debug({
        "message": "Events processed from records",
        "events": events
    })

    send_events(events)
