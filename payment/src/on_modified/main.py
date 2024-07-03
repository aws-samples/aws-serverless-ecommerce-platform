"""
OnModified Function
"""


import os
import boto3
import requests
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging.logger import Logger # pylint: disable=import-error
from aws_lambda_powertools import Metrics # pylint: disable=import-error
from aws_lambda_powertools.metrics import MetricUnit # pylint: disable=import-error


API_URL = os.environ["API_URL"]
ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name
metrics = Metrics(namespace="ecommerce.payment") # pylint: disable=invalid-name


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


@metrics.log_metrics(raise_on_empty_metrics=False)
@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda handler
    """

    order_id = event["detail"]["new"]["orderId"]
    new_total = event["detail"]["new"]["total"]
    old_total = event["detail"]["old"]["total"]

    logger.info({
        "message": "Received modification of order {}".format(order_id),
        "orderId": order_id,
        "old_amount": old_total,
        "new_amount": new_total
    })

    payment_token = get_payment_token(order_id)
    update_payment_amount(payment_token, new_total)

    # Add custom metrics
    metrics.add_dimension(name="environment", value=ENVIRONMENT)
    difference = new_total - old_total
    if difference < 0:
        metric = "amountLost"
    else:
        metric = "amountWon"
    metrics.add_metric(name=metric, unit=MetricUnit.Count, value=abs(difference))
