"""
GetOrdersFunction
"""


import os
from typing import Optional
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context
import boto3
from ecom.helpers import message # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = logger_setup() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def get_order(order_id: str) -> Optional[dict]:
    """
    Returns order from DynamoDB
    """

    # Send request to DynamoDB
    response = table.get_item(Key={"orderId": order_id}) # pylint: disable=no-member
    order = response.get("Item", None)

    # Log retrieved informations
    if order is None:
        logger.warning({
            "message": "No order retrieved for the order ID",
            "orderId": order_id
        })
    else:
        logger.debug({
            "message": "Order retrieved",
            "order": order
        })

    return order


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler for GetOrder
    """

    logger.debug({"message": "Event received", "event": event})

    # Retrieve the userId
    try:
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        iam_user = False
        logger.info({"message": "Received get order from user", "userId": user_id})
        tracer.put_annotation("userId", user_id)
        tracer.put_annotation("iamUser", False)
    # API Gateway should ensure that the claims are present, but checking here
    # protects against configuration errors.
    except KeyError:
        # Check if there is an IAM user ARN
        try:
            user_id = event["requestContext"]["identity"]["userArn"]
            iam_user = True
            logger.info({"message": "Received get order from IAM user", "userArn": user_id})
            tracer.put_annotation("userArn", user_id)
            tracer.put_annotation("iamUser", True)
        except KeyError:
            logger.warning({"message": "User ID not found in event"})
            return message("Unauthorized", 401)

    # Retrieve the orderId
    try:
        order_id = event["pathParameters"]["orderId"]
    except (KeyError, TypeError):
        logger.warning({"message": "Order ID not found in event"})
        return message("Missing orderId", 400)

    # Retrieve the order from DynamoDB
    order = get_order(order_id)

    # Check that the order can be sent to the user
    # This includes both when the item is not found and when the user IDs do
    # not match.
    if order is None or (not iam_user and user_id != order["userId"]):
        return message("Order not found", 404)

    # Send the response
    return message(order)
