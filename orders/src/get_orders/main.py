"""
GetOrdersFunction
"""


import datetime
import decimal
import json
import os
from typing import List, Optional, Set, Union
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context
import boto3
from boto3.dynamodb.conditions import Key


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]
USER_INDEX_NAME = os.environ["USER_INDEX_NAME"]
ORDERS_LIMIT = int(os.environ["ORDERS_LIMIT"])


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = logger_setup() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


class Encoder(json.JSONEncoder):
    """
    Helper class to convert a DynamoDB item to JSON
    """

    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            return int(o)
        return super(Encoder, self).default(o)


def message(msg: Union[dict, str], status_code: int = 200) -> dict:
    """
    Prepares a message for API Gateway
    """

    if isinstance(msg, str):
        msg = {"message": msg}

    return  {
        "statusCode": status_code,
        "body": json.dumps(msg, cls=Encoder)
    }


@tracer.capture_method
def get_orders(user_id: str, next_token: Optional[str]) -> Set[List[dict], Optional[str]]:
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
    response = dynamodb.query(**kwargs) # pylint: disable=no-member
    orders = response.get("Items", [])

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
    if not response.get("LastEvaluatedKey", None):
        return (orders, None)
    else:
        return (orders, response["LastEvaluatedKey"]["createdDate"])


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler for GetOrders
    """

    # Retrieve the userId
    try:
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        logger.debug({"message": "Received get orders for user", "userId": user_id})
        tracer.put_annotation("userId", user_id)
    # API Gateway should ensure that the claims are present, but checking here
    # protects against configuration errors.
    except KeyError:
        return message("Forbidden", 403)

    # Gather the next token, if any
    next_token = event["queryStringParameters"].get("nextToken", None)
    
    # Retrieve orders from DynamoDB
    orders, new_next_token = get_orders(user_id, next_token)

    # Send the response
    response = {
        "orders": orders
    }
    if new_next_token is not None:
        response["nextToken"] = new_next_token
    return message(response)