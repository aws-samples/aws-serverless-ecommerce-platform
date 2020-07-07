"""
OnPackageCreatedFunction
"""


import os
from typing import Optional
from urllib.parse import urlparse
import boto3
import requests # pylint: disable=import-error
from aws_requests_auth.boto_utils import BotoAWSRequestsAuth # pylint: disable=import-error
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging.logger import Logger # pylint: disable=import-error
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit


ENVIRONMENT = os.environ["ENVIRONMENT"]
ORDERS_API_URL = os.environ["ORDERS_API_URL"]
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name
metrics = Metrics(namespace="ecommerce.delivery", service="delivery")


@tracer.capture_method
def get_order(order_id: str) -> Optional[dict]:
    """
    Retrieve the order from ther Orders service
    """

    logger.debug({
        "message": "Retreiving order {}".format(order_id),
        "orderId": order_id
    })

    # Create IAM signature helper
    request_url = ORDERS_API_URL + order_id
    url = urlparse(request_url)
    region = boto3.session.Session().region_name
    auth = BotoAWSRequestsAuth(aws_host=url.netloc,
                               aws_region=region,
                               aws_service='execute-api')

    # Send request to order service
    response = requests.get(request_url, auth=auth)

    if response.status_code != 200:
        logger.error({
            "message": "Failed to retrieve order {}".format(order_id),
            "orderId": order_id,
            "statusCode": response.status_code,
            "response": response.json()
        })
        return None

    order = response.json()

    logger.info({
        "message": "Retrieved order {} from Orders service".format(order_id),
        "orderId": order_id,
        "order": order
    })
    return order


@tracer.capture_method
def save_shipping_request(order: dict) -> None:
    """
    Save the shipping request to DynamoDB
    """

    result = table.get_item(Key={
        "orderId": order["orderId"]
    })

    if result.get("Item", {}).get("status", "NEW") != "NEW":
        logger.info({
            "message": "Cannot update shipping request in status '{}'".format(result["Item"]["status"]),
            "orderId": order["orderId"]
        })
        return

    # We only care about the order ID (partition key) and address
    table.put_item(Item={
        "orderId": order["orderId"],
        # Used for the GSI
        "isNew": "true",
        "status": "NEW",
        "address": order["address"]
    })

    metrics.add_metric(name="deliveryCreated", unit=MetricUnit.Count, value=1)


@metrics.log_metrics
@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    """
    Lambda function handler
    """

    metrics.add_dimension(name="environment", value=ENVIRONMENT)

    # This should only receive PackageCreated events
    assert event["source"] == "ecommerce.warehouse"
    assert event["detail-type"] == "PackageCreated"

    try:
        order_id = event["detail"]["orderId"]
    except KeyError as exc:
        logger.warning({
            "message": "Failed to retrieve orderId from PackageCreated event",
            "event": event,
            "exception": str(exc)
        })
        raise exc

    logger.debug({
        "message": "Received PackageCreated message for order {}".format(order_id),
        "orderId": order_id
    })

    # Retrieve order from order service
    order = get_order(order_id)

    if order is None:
        logger.warning({
            "message": "Failed to retrieve order {}".format(order_id),
            "orderId": order_id
        })
        raise Exception("Failed to retrieve order {}".format(order_id))

    # Save the order to the database
    logger.debug({
        "message": "Saving the shipping request to the database",
        "orderId": order_id,
        "order": order
    })
    save_shipping_request(order)
