"""
CreateOrderFunction
"""


import asyncio
import datetime
import json
import os
from typing import List, Tuple
from urllib.parse import urlparse
import uuid
import boto3
import jsonschema
import requests
from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
PRODUCTS_API_URL = os.environ["PRODUCTS_API_URL"]
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.json")
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = logger_setup() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


with open(SCHEMA_FILE) as fp:
    schema = json.load(fp) # pylint: disable=invalid-name


@tracer.capture_method
async def validate_delivery(order: dict) -> Tuple[bool, str]:
    """
    Validate the delivery price
    """

    # TODO
    return (True, "")


@tracer.capture_method
async def validate_payment(order: dict) -> Tuple[bool, str]:
    """
    Validate the payment token
    """

    # TODO
    return (True, "")


@tracer.capture_method
async def validate_products(order: dict) -> Tuple[bool, str]:
    """
    Validate the products in the order
    """

    # Gather the domain name and AWS region
    url = urlparse(PRODUCTS_API_URL)
    region = boto3.session.Session().region_name
    # Create the signature helper
    iam_auth = BotoAWSRequestsAuth(aws_host=url.netloc,
                                   aws_region=region,
                                   aws_service='execute-api')
    # Send a POST request
    response = requests.post(
        PRODUCTS_API_URL+"/backend/validate",
        json={"products": order["products"]},
        auth=iam_auth
    )

    logger.debug({
        "message": "Response received from products",
        "body": response.json()
    })

    body = response.json()
    return (len(body.get("products", [])) == 0, body.get("message", ""))


@tracer.capture_method
async def validate(order: dict) -> List[str]:
    """
    Returns a list of error messages
    """

    error_msgs = []
    for valid, error_msg in await asyncio.gather(
            validate_delivery(order),
            validate_payment(order),
            validate_products(order)):
        if not valid:
            error_msgs.append(error_msg)

    if error_msgs:
        logger.info({
            "message": "Validation errors for order",
            "order": order,
            "errors": error_msgs
        })

    return error_msgs


@tracer.capture_method
def cleanup_products(products: List[dict]) -> List[dict]:
    """
    Cleanup products
    """

    return [{
        "productId": product["productId"],
        "name": product["name"],
        "package": product["package"],
        "price": product["price"],
        "quantity": product.get("quantity", 1)
    } for product in products]


@tracer.capture_method
def inject_order_fields(order: dict) -> dict:
    """
    Inject fields into the order and return the order
    """

    now = datetime.datetime.now()

    order["orderId"] = str(uuid.uuid4())
    order["createdDate"] = now.isoformat()
    order["modifiedDate"] = now.isoformat()
    order["total"] = sum([p["price"]*p.get("quantity", 1) for p in order["products"]]) + order["deliveryPrice"]

    return order


@tracer.capture_method
def store_order(order: dict) -> None:
    """
    Store the order in DynamoDB
    """

    logger.debug({
        "message": "Store order",
        "order": order
    })

    table.put_item(Item=order)


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler
    """

    # Basic checks on the event
    for key in ["order", "userId"]:
        if key not in event:
            return {
                "success": False,
                "message": "Invalid event",
                "errors": ["Missing {} in event".format(key)]
            }

    # Inject userId into the order
    order = event["order"]
    order["userId"] = event["userId"]

    # Validate the schema of the order
    try:
        jsonschema.validate(order, schema)
    except jsonschema.ValidationError as exc:
        return {
            "success": False,
            "message": "JSON Schema validation error",
            "errors": [str(exc)]
        }

    # Cleanup products
    order["products"] = cleanup_products(order["products"])

    # Inject fields in the order
    order = inject_order_fields(order)

    # Validate the order against other services
    error_msgs = asyncio.run(validate(order))
    if len(error_msgs) > 0:
        return {
            "success": False,
            "message": "Validation errors",
            "errors": error_msgs
        }

    store_order(order)

    return {
        "success": True,
        "order": order,
        "message": "Order created"
    }
