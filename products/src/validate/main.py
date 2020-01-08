"""
ValidateFunction
"""


import os
import boto3


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


table = boto3.resource("dynamodb").Table(TABLE_NAME)


def handler(event, context):
    return {
        "statusCode": 200,
        "body": "This is a test"
    }