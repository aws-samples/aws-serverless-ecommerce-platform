"""
ValidateFunction
"""

import json
import os
import requests
from aws_lambda_powertools.tracing import Tracer #pylint: disable=import-error
from aws_lambda_powertools.logging.logger import Logger #pylint: disable=import-error
from ecom.apigateway import iam_user_id, response # pylint: disable=import-error


API_URL = os.environ["API_URL"]
ENVIRONMENT = os.environ["ENVIRONMENT"]


logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def validate_payment_token(payment_token: str, total: int) -> bool:
    """
    Validate a payment token for a given total
    """

    # Send the request to the 3p service
    res = requests.post(API_URL+"/check", json={
        "paymentToken": payment_token,
        "amount": total
    })

    body = res.json()
    if "ok" not in body:
        logger.error({
            "message": "Missing 'ok' in 3rd party response body",
            "body": body,
            "paymentToken": payment_token
        })
    return body.get("ok", False)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler
    """

    user_id = iam_user_id(event)
    if user_id is None:
        logger.warning({"message": "User ARN not found in event"})
        return response("Unauthorized", 401)

    # Extract the body
    try:
        body = json.loads(event["body"])
    except Exception as exc: # pylint: disable=broad-except
        logger.warning("Exception caught: %s", exc)
        return response("Failed to parse JSON body", 400)

    for key in ["paymentToken", "total"]:
        if key not in body:
            logger.warning({
                "message": "Missing '{}' in request body.".format(key),
                "body": body
            })
            return response("Missing '{}' in request body.".format(key), 400)

    valid = validate_payment_token(body["paymentToken"], body["total"])

    return response({
        "ok": valid
    })
