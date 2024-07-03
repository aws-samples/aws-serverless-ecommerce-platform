"""
OnEvents Lambda function
"""


import json
import os
from typing import List
import boto3
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging.logger import Logger # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
API_URL = os.environ["LISTENER_API_URL"]
TABLE_NAME = os.environ["LISTENER_TABLE_NAME"]


apigwmgmt = boto3.client("apigatewaymanagementapi", endpoint_url=API_URL) # pylint: disable=invalid-name
dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def get_connection_ids(service_name: str) -> List[str]:
    """
    Retrieve connection IDs for a service name
    """

    res = table.query(
        IndexName="listener-service",
        KeyConditionExpression=Key("service").eq(service_name),
        # Only check for 100 connections
        Limit=100
    )

    return [c["id"] for c in res.get("Items", [])]


@tracer.capture_method
def send_event(event: dict, connection_ids: List[str]):
    """
    Send an event to a list of connection IDs
    """

    for connection_id in connection_ids:
        try:
            apigwmgmt.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps(event).encode("utf-8")
            )
        # The client is disconnected, we can safely ignore and move to the
        # next connection ID.
        except apigwmgmt.exceptions.GoneException:
            continue


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda handler
    """

    # Get the service name
    service_name = event["source"]
    logger.debug({
        "message": "Receive event from {}".format(service_name),
        "serviceName": service_name,
        "event": event
    })

    # Get connection IDs
    connection_ids = get_connection_ids(service_name)

    # Send event to connected users
    send_event(event, connection_ids)
