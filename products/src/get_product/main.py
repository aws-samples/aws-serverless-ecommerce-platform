"""
GetProductFunction
"""


import os
from typing import Optional
import boto3
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context
from ecom.apigateway import response # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


logger = logger_setup() # pylint: disable=invalid-name
table = boto3.resource("dynamodb").Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def get_product(product_id: str) -> Optional[dict]:
    """
    Retrieve the product from DynamoDB
    """

    res = table.get_item(Key={"productId": product_id}) # pylint: disable=no-member
    product = res.get("Item", None)

    # Log retrieved informations
    if product is None:
        logger.info({
            "message": "No product retrieved for the product ID",
            "productId": product_id
        })
    else:
        logger.debug({
            "message": "Product retrieved",
            "product": product
        })

    return product


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Handler for GetProductFunction
    """

    logger.debug({"message": "Event received", "event": event})

    # Retrieve the productId
    try:
        product_id = event["pathParameters"]["productId"]
    except (KeyError, TypeError):
        logger.warning({"message": "Product ID not found in event"})
        return response("Missing productId", 400)

    # Retrieve the product
    product = get_product(product_id)

    # 404: Product Not Found
    if product is None:
        return response({"message": "Product Not Found"}, 404)

    # Send the product
    return response(product)
