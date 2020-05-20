"""
PricingFunction
"""


import json
import math
from typing import List
import os
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging.logger import Logger # pylint: disable=import-error
from ecom.apigateway import iam_user_id, response # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]


logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


# 50*50*50 cm cube
BOX_VOLUME = 500*500*500
# 12kg per box
BOX_WEIGHT = 12000


COUNTRY_SHIPPING_FEES = {
    # Nordics countries
    "DK":    0, "FI":    0, "NO":    0, "SE":    0,

    # Other EU countries
    "AT": 1000, "BE": 1000, "BG": 1000, "CY": 1000,
    "CZ": 1000, "DE": 1000, "EE": 1000, "ES": 1000,
    "FR": 1000, "GR": 1000, "HR": 1000, "HU": 1000,
    "IE": 1000, "IT": 1000, "LT": 1000, "LU": 1000,
    "LV": 1000, "MT": 1000, "NL": 1000, "PO": 1000,
    "PT": 1000, "RO": 1000, "SI": 1000, "SK": 1000,

    # North America
    "CA": 1500, "US": 1500,

    # Rest of the world
    "*": 2500
}


@tracer.capture_method
def count_boxes(packages: List[dict]) -> int:
    """
    Count number of boxes based on the product packaging
    """

    volume = sum([p["width"]*p["length"]*p["height"] for p in packages])
    weight = sum([p["weight"] for p in packages])

    return max(math.ceil(volume/BOX_VOLUME), math.ceil(weight/BOX_WEIGHT))


@tracer.capture_method
def get_shipping_cost(address: dict) -> int:
    """
    Get the shipping cost per box
    """

    return COUNTRY_SHIPPING_FEES.get(address["country"], COUNTRY_SHIPPING_FEES["*"])


@tracer.capture_method
def get_pricing(products: List[dict], address: dict) -> int:
    """
    Calculate the delivery cost for a specific address and list of products
    """

    return count_boxes([p["package"] for p in products]) * get_shipping_cost(address)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler for /backend/pricing
    """

    # Verify that this is a request with IAM credentials
    if iam_user_id(event) is None:
        logger.warning({"message": "User ARN not found in event"})
        return response("Unauthorized", 403)

    # Extract the request body
    try:
        body = json.loads(event["body"])
    except Exception as exc: # pylint: disable=broad-except
        logger.warning("Exception caught: %s", exc)
        return response("Failed to parse JSON body", 400)

    for key in ["products", "address"]:
        if key not in body:
            logger.info({
                "message": "Missing '{}' in body".format(key),
                "body": body
            })
            return response("Missing '{}' in body".format(key), 400)

    # Calculate the delivery pricing
    pricing = get_pricing(body["products"], body["address"])
    logger.debug({
        "message": "Estimated delivery pricing to {}".format(pricing),
        "pricing": pricing
    })

    # Send the response back
    return response({
        "pricing": pricing
    })
