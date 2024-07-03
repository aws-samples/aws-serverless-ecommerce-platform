"""
Register Lambda function
"""


import datetime
import json
import os
import boto3
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging.logger import Logger # pylint: disable=import-error
from ecom.apigateway import response # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["LISTENER_TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def register_service(connection_id: str, service_name: str):
    """
    Store the connectionId in DynamoDB
    """

    ttl = datetime.datetime.now() + datetime.timedelta(days=1)

    table.put_item(Item={
        "id": connection_id,
        "service": service_name,
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

    try:
        body = json.loads(event["body"])
    except json.decoder.JSONDecodeError:
        logger.error({
            "message": "Failed to parse request body",
            "event": event
        })
        return response("Failed to parse request body", 400)

    try:
        body = json.loads(event["body"])
        service_name = body["serviceName"]
    except (KeyError, TypeError):
        logger.warning({
            "message": "Missing 'serviceName' in request body",
            "event": event
        })
        return response("Missing 'serviceName' in request body", 400)

    logger.debug({
        "message": f"Register {connection_id} with service '{service_name}'",
        "event": event
    })

    register_service(connection_id, service_name)

    return response("Connected")
