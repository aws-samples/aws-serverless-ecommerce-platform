"""
OnFailed Function
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
def delete_payment_token(order_id: str) -> None:
    """
    Delete the paymentToken in DynamoDB
    """

    table.delete_item(Key={
        "orderId": order_id,
    })


@tracer.capture_method
def cancel_payment(payment_token: str) -> None:
    """
    Cancel the payment request
    """

    response = requests.post(API_URL+"/cancelPayment", json={
        "paymentToken": payment_token
    })

    if not response.json().get("ok", False):
        raise Exception("Failed to process payment: {}".format(response.json().get("message", "No error message")))


@metrics.log_metrics(raise_on_empty_metrics=False)
@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda handler
    """

    order_id = event["detail"]["orderId"]

    logger.info({
        "message": "Received failed order {}".format(order_id),
        "orderId": order_id
    })

    payment_token = get_payment_token(order_id)
    cancel_payment(payment_token)
    delete_payment_token(order_id)

    # Add custom metrics
    amount_lost = event["detail"]["total"]

    metrics.add_dimension(name="environment", value=ENVIRONMENT)
    metrics.add_metric(name="paymentCancelled", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="amountLost", unit=MetricUnit.Count, value=amount_lost)
