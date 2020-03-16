"""
OnModified Function
"""


import os
import boto3
import requests
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context # pylint: disable=import-error


API_URL = os.environ["3P_API_URL"]
ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = logger_setup() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def get_payment_token(order_id: str) -> str:
    """
    Retrieve the paymentToken from DynamoDB
    """

    response = table.get_item(Key={
        "orderId": order_id
    })

    return response["Item"]["paymentToken"]


@tracer.capture_method
def update_payment_amount(payment_token: str, amount: int) -> None:
    """
    Update the payment amount
    """

    response = requests.post(API_URL+"/updateAmount", json={
        "paymentToken": payment_token,
        "amount": amount
    })

    body = response.json()
    if "message" in body:
        raise Exception("Error updating amount: {}".format(body["message"]))


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda handler
    """

    order_id = event["detail"]["new"]["orderId"]
    total = event["detail"]["new"]["total"]

    logger.info({
        "message": "Received completed order {}".format(order_id),
        "orderId": order_id
    })

    payment_token = get_payment_token(order_id)
    update_payment_amount(payment_token, total)
