"""
ValidateFunction
"""


import decimal
import json
import os
from typing import List, Optional, Union, Set
import boto3
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


logger = logger_setup()
table = boto3.resource("dynamodb").Table(TABLE_NAME)
tracer = Tracer()


class DecimalEncoder(json.JSONEncoder):
    """
    Helper class to convert a DynamoDB item to JSON
    """
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


def message(msg: Union[dict, str], status_code:int = 200) -> dict:
    """
    Prepares a message for API Gateway
    """

    if isinstance(msg, str):
        msg = {"message": msg}

    return  {
        "statusCode": status_code,
        "body": json.dumps(msg, cls=DecimalEncoder)
    }


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
            return ddb_product, "Invalid value for '{}': want '{}', got '{}' in product '{}'".format(key, ddb_product[key], user_product[key], user_product["productId"])

    # All good, return nothing
    return



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

@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    """
    Lambda function handler for /backend/validate
    """

    # Extract the list of products
    try:
        body = json.loads(event["body"])
    except:
        logger.warn()
        return message("Failed to parse JSON body", 400)

    if "products" not in body:
        return message("Missing 'products' in body", 400)

    products, reason = validate_products(body["products"])

    if len(products) > 0:
        return message({
            "message": reason,
            "products": products
        }, 400)

    return message("All products are valid")
