"""
ValidateFunction
"""


import json
import os
from typing import List, Optional, Union, Set
import boto3
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging.logger import Logger
from ecom.apigateway import iam_user_id, response # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


logger = Logger() # pylint: disable=invalid-name
table = boto3.resource("dynamodb").Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def compare_product(user_product: dict, ddb_product: Optional[dict]) -> Optional[Set[Union[dict, str]]]:
    """
    Compare the user-provided product with the data provided by DynamoDB
    """

    if ddb_product is None:
        return user_product, "Product '{}' not found".format(user_product["productId"])

    # Validate schema
    for key in ddb_product.keys():
        if key not in user_product:
            return ddb_product, "Missing '{}' in product '{}'".format(key, user_product["productId"])

        if user_product[key] != ddb_product[key]:
            return ddb_product, "Invalid value for '{}': want '{}', got '{}' in product '{}'".format(
                key, ddb_product[key], user_product[key], user_product["productId"]
            )

    # All good, return nothing
    return None


@tracer.capture_method
def validate_product(product: dict) -> Optional[Set[Union[dict, str]]]:
    """
    Validate a single product
    """

    if "productId" not in product:
        return product, "Missing 'productId' in product"

    tracer.put_annotation("productId", product["productId"])

    # Fetch item in DynamoDB
    ddb_product = table.get_item(
        Key={"productId": product["productId"]},
        ProjectionExpression="#productId, #name, #package, #price",
        ExpressionAttributeNames={
            "#productId": "productId",
            "#name": "name",
            "#package": "package",
            "#price": "price"
        }
    ).get("Item", None)

    return compare_product(product, ddb_product)


@tracer.capture_method
def validate_products(products: List[dict]) -> Set[Union[List[dict], str]]:
    """
    Takes a list of products and validate them

    If all products are valid, this will return an empty list.
    """

    validated_products = []
    reasons = []

    for product in products:
        retval = validate_product(product)
        if retval is not None:
            validated_products.append(retval[0])
            reasons.append(retval[1])

    return validated_products, ". ".join(reasons)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler for /backend/validate
    """

    user_id = iam_user_id(event)
    if user_id is None:
        logger.warning({"message": "User ARN not found in event"})
        return response("Unauthorized", 401)

    # Extract the list of products
    try:
        body = json.loads(event["body"])
    except Exception as exc: # pylint: disable=broad-except
        logger.warning("Exception caught: %s", exc)
        return response("Failed to parse JSON body", 400)

    if "products" not in body:
        return response("Missing 'products' in body", 400)

    products, reason = validate_products(body["products"])

    if len(products) > 0:
        return response({
            "message": reason,
            "products": products
        }, 200)

    return response("All products are valid")
