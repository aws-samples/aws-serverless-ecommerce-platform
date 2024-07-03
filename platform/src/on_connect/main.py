"""
OnConnect Lambda function
"""


import datetime
import os
import boto3
from botocore.waiter import WaiterModel, create_waiter_with_client
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging.logger import Logger # pylint: disable=import-error
from ecom.apigateway import response # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
EVENT_BUS_NAME, EVENT_RULE_NAME = os.environ["EVENT_RULE_NAME"].split("|")
TABLE_NAME = os.environ["LISTENER_TABLE_NAME"]
WAITER_MAX_ATTEMPTS = 5
WAITER_DELAY = 2

dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
eventbridge = boto3.client("events") #pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def store_id(connection_id: str):
    """
    Store the connectionId in DynamoDB
    """

    ttl = datetime.datetime.now() + datetime.timedelta(days=1)

    table.put_item(Item={
        "id": connection_id,
        "ttl": int(ttl.timestamp())
    })


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda handler
    """

    try:
        connection_id = event["requestContext"]["connectionId"]
    except (KeyError, TypeError):
        logger.error({
            "message": "Missing connection ID in event",
            "event": event
        })
        return response("Missing connection ID", 400)

    logger.debug({
        "message": f"New connection {connection_id}",
        "event": event
    })

    store_id(connection_id)

    return response("Connected")
