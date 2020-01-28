"""
GetOrdersFunction
"""


import os
from typing import List, Optional, Set, Union
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context
import boto3
from boto3.dynamodb.conditions import Key
from ecom.apigateway import cognito_user_id, response # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]
USER_INDEX_NAME = os.environ["USER_INDEX_NAME"]
ORDERS_LIMIT = int(os.environ["ORDERS_LIMIT"])


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = logger_setup() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def get_orders(user_id: str, next_token: Optional[str]) -> Set[Union[List[dict], Optional[str]]]:
    """
    Returns orders from DynamoDB
    """

    # Prepare query
    kwargs = {
        "IndexName": USER_INDEX_NAME,
        "Select": "ALL_ATTRIBUTES",
        "Limit": ORDERS_LIMIT,
        "KeyConditionExpression": Key("userId").eq(user_id)
    }
    # Inject the continuation token
    if next_token is not None:
        kwargs["ExclusiveStartKey"] = {
            "userId": user_id,
            "createdDate": next_token
        }

    # Log DynamoDB query
    logger.debug({
        "message": "Sending query to DynamoDB",
        "userId": user_id,
        "nextToken": next_token,
        "query": kwargs
    })

    # Send request to DynamoDB
    res = table.query(**kwargs) # pylint: disable=no-member
    orders = res.get("Items", [])

    # Log retrieved informations
    logger.info({
        "message": "Retrieved {} orders for userId".format(len(orders)),
        "userId": user_id,
        "nextToken": next_token,
        "ordersCount": len(orders)
    })
    logger.debug({
        "message": "Retrieved {} orders for userId".format(len(orders)),
        "userId": user_id,
        "nextToken": next_token,
        "orders": orders
    })

    # From: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Table.query
    # If LastEvaluatedKey is empty, then the "last page" of results has been
    # processed and there is no more data to be retrieved.
    return (orders, res.get("LastEvaluatedKey", {}).get("createdDate", None))


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler for GetOrders
    """

    logger.debug({"message": "Event received", "event": event})

    # Retrieve the userId
    user_id = cognito_user_id(event)
    if user_id is not None:
        logger.info({"message": "Received get orders for user", "userId": user_id})
        tracer.put_annotation("userId", user_id)
    else:
        logger.warning({"message": "User ID not found in event"})
        return response("Forbidden", 403)

    # Gather the next token, if any
    # event["queryStringParameters"] == None if there is no query string
    try:
        next_token = event["queryStringParameters"]["nextToken"]
    except TypeError:
        next_token = None

    # Retrieve orders from DynamoDB
    orders, new_next_token = get_orders(user_id, next_token)

    # Send the response
    body = {
        "orders": orders
    }
    if new_next_token is not None:
        body["nextToken"] = new_next_token
    return response(body)
