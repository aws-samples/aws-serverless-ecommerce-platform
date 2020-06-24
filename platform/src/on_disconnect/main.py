"""
OnDisconnect Lambda function
"""


import os
import boto3
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging.logger import Logger # pylint: disable=import-error
from ecom.apigateway import response # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
EVENT_BUS_NAME, EVENT_RULE_NAME = os.environ["EVENT_RULE_NAME"].split("|")
TABLE_NAME = os.environ["LISTENER_TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
eventbridge = boto3.client("events") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def delete_id(connection_id: str):
    """
    Delete the connectionId in DynamoDB
    """

    table.delete_item(Key={
        "id": connection_id
    })


@tracer.capture_method
def disable_rule():
    """
    Disable EventBridge rule
    """

    # Check for active connextions
    res = table.scan(Limit=1, ConsistentRead=True)
    if res.get("Items"):
        # Active connections, skipping
        logger.info({
            "message": "Keeping rule enabled due to active connections"
        })
        return

    # Disable the rule
    eventbridge.disable_rule(
        Name=EVENT_RULE_NAME,
        EventBusName=EVENT_BUS_NAME
    )


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
        "message": f"Connection {connection_id} closing",
        "event": event
    })

    # disable_rule must happen after delete_id, as it checks if there are
    # active connections before deleting the rule.
    delete_id(connection_id)
    disable_rule()

    return response("Disconnected")
