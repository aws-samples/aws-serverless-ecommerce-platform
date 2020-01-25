"""
Helpers for Lambda functions
"""


from datetime import datetime, date
from decimal import Decimal
import json
from typing import Dict, Union


__all__ = ["Encoder", "message"]


class Encoder(json.JSONEncoder):
    """
    Helper class to convert a DynamoDB item to JSON
    """

    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, datetime) or isinstance(o, date):
            return o.isoformat()
        if isinstance(o, Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            return int(o)
        return super(Encoder, self).default(o)


def message(msg: Union[dict, str], status_code: int = 200) -> Dict[str, Union[int, str]]:
    """
    Prepares a message for API Gateway
    """

    if isinstance(msg, str):
        msg = {"message": msg}

    return  {
        "statusCode": status_code,
        "body": json.dumps(msg, cls=Encoder)
    }