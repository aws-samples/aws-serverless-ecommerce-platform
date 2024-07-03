"""
GetOrdersFunction
"""


import os
from typing import Optional
import boto3
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging.logger import Logger # pylint: disable=import-error
from ecom.apigateway import iam_user_id, response # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def get_order(order_id: str) -> Optional[dict]:
    """
    Returns order from DynamoDB
    """

    # Send request to DynamoDB
    res = table.get_item(Key={"orderId": order_id}) # pylint: disable=no-member
    order = res.get("Item", None)

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


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler for GetOrder
    """

    logger.debug({"message": "Event received", "event": event})

    # Retrieve the userId
    user_id = iam_user_id(event)
    if user_id is not None:
        logger.info({"message": "Received get order from IAM user", "userArn": user_id})
        tracer.put_annotation("userArn", user_id)
        tracer.put_annotation("iamUser", True)
        iam_user = True
    else:
        logger.warning({"message": "User ID not found in event"})
        return response("Unauthorized", 401)

    # Retrieve the orderId
    try:
        order_id = event["pathParameters"]["orderId"]
    except (KeyError, TypeError):
        logger.warning({"message": "Order ID not found in event"})
        return response("Missing orderId", 400)

    # Set a trace annotation
    tracer.put_annotation("orderId", order_id)

    # Retrieve the order from DynamoDB
    order = get_order(order_id)

    # Check that the order can be sent to the user
    # This includes both when the item is not found and when the user IDs do
    # not match.
    if order is None or (not iam_user and user_id != order["userId"]):
        return response("Order not found", 404)

    # Send the response
    return response(order)
