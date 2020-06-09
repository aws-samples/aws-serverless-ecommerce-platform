"""
ValidateFunction
"""


import json
import os
from typing import List, Optional, Union, Set
import boto3
from boto3.dynamodb.types import TypeDeserializer
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging.logger import Logger
from ecom.apigateway import iam_user_id, response # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.client("dynamodb") # pylint: disable=invalid-name
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name
type_deserializer = TypeDeserializer() # pylint: disable=invalid-name


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
def validate_products(products: List[dict]) -> Set[Union[List[dict], str]]:
    """
    Takes a list of products and validate them

    If all products are valid, this will return an empty list.
    """

    validated_products = []
    reasons = []

    # batch_get_item only supports up to 100 items, so split the list of products in batches
    # of 100 max.
    for i in range(0, len(products), 100):
        q_products = {}
        for product in products[i:i+100]:
            q_products[product["productId"]] = product

        response = dynamodb.batch_get_item(RequestItems={
            TABLE_NAME: {
                "Keys": [
                    {"productId": {"S": product_id}}
                    # Only fetch by batch of 100 items
                    for product_id in q_products.keys()
                ],
                "ProjectionExpression": "#productId, #name, #package, #price",
                "ExpressionAttributeNames": {
                    "#productId": "productId",
                    "#name": "name",
                    "#package": "package",
                    "#price": "price"
                }
            }
        })

        ddb_products = {
            p["productId"]["S"]: {k: type_deserializer.deserialize(v) for k, v in p.items()}
            for p in response.get("Responses", {}).get(TABLE_NAME, [])
        }

        # Even if we ask less than 100 items, there is a 16MB response limit, so the call might
        # return less items than expected.
        while response.get("UnprocessedKeys", {}).get(TABLE_NAME, None) is not None:
            response = dynamodb.batch_get_item(RequestItems=response["UnprocessedKeys"])

            for product in response.get("Responses", {}).get(TABLE_NAME, []):
                ddb_products[product["productId"]["S"]] = {k: type_deserializer.deserialize(v) for k, v in product.items()}

        for product_id, product in q_products.items():
            retval = compare_product(product, ddb_products.get(product_id, None))
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
