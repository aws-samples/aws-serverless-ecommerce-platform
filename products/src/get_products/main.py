"""
GetProductFunction
"""


import os
from typing import List, Optional, Tuple
import boto3
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context
from ecom.helpers import message # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


logger = logger_setup() # pylint: disable=invalid-name
table = boto3.resource("dynamodb").Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def get_products(next_token: Optional[str] = None) -> Tuple[List[dict], Optional[str]]:
    """
    Retrieve products from DynamoDB
    """

    kwargs = {
        "Limit": 20
    }
    if next_token is not None:
        kwargs["ExclusiveStartKey"] = {"productId": next_token}

    response = table.scan(**kwargs)

    products = response.get("Items", [])

    # Log retrieved informations
    if len(products) == 0:
        logger.info({
            "message": "No products retrieved"
        })
    else:
        logger.debug({
            "message": "{} product(s) retrieved".format(len(products)),
            "productCount": len(products)
        })

    next_token = response.get("LastEvaluatedKey", {}).get("productId", None)

    return products, next_token


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Handler for GetProductFunction
    """

    logger.debug({"message": "Event received", "event": event})

    # Gather the next token, if any
    # event["queryStringParameters"] == None if there is no query string
    try:
        next_token = event["queryStringParameters"]["nextToken"]
    except TypeError:
        next_token = None

    # Retrieve products
    products, next_token = get_products(next_token)

    # Send the list of products
    retval = {"products": products}
    if next_token is not None:
        retval["nextToken"] = next_token

    return message(retval)
