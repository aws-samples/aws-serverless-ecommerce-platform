"""
API Gateway helpers for Lambda functions
"""


import json
from typing import Dict, Optional, Union
from .helpers import Encoder


__all__ = [
    "cognito_user_id", "iam_user_id", "response"
]


def cognito_user_id(event: dict) -> Optional[str]:
    """
    Returns the User ID (sub) from cognito or None
    """

    try:
        return event["requestContext"]["authorizer"]["claims"]["sub"]
    except (TypeError, KeyError):
        return None


def iam_user_id(event: dict) -> Optional[str]:
    """
    Returns the User ID (ARN) from IAM or None
    """

    try:
        return event["requestContext"]["identity"]["userArn"]
    except (TypeError, KeyError):
        return None


def response(
        msg: Union[dict, str],
        status_code: int = 200,
        allow_origin: str = "*",
        allow_headers: str = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,x-requested-with",
        allow_methods: str = "GET,POST,PUT,DELETE,OPTIONS"
    ) -> Dict[str, Union[int, str]]:
    """
    Returns a response for API Gateway
    """

    if isinstance(msg, str):
        msg = {"message": msg}

    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Headers": allow_headers,
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Methods": allow_methods
        },
        "body": json.dumps(msg, cls=Encoder)
    }
