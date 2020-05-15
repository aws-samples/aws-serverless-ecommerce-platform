"""
OnCreated Function
"""


import os
import boto3
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging.logger import Logger # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def save_payment_token(order_id: str, payment_token: str) -> None:
    """
    Save the paymentToken in DynamoDB
    """

    table.put_item(Item={
        "orderId": order_id,
        "paymentToken": payment_token
    })


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda handler
    """

    order_id = event["detail"]["orderId"]
    payment_token = event["detail"]["paymentToken"]

    logger.info({
        "message": "Received new order {}".format(order_id),
        "orderId": order_id,
        "paymentToken": payment_token
    })

    save_payment_token(order_id, payment_token)
