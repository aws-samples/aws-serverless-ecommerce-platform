"""
SignUpFunction
"""


import datetime
import json
import os
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging.logger import Logger
import boto3


ENVIRONMENT = os.environ["ENVIRONMENT"]
EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]


eventbridge = boto3.client("events") # pylint: disable=invalid-name
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def process_request(input_: dict) -> dict:
    """
    Transform the input request into an EventBridge event
    """

    output = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.users",
        "Resources": [input_["userName"]],
        "DetailType": "UserCreated",
        "Detail": json.dumps({
            "userId": input_["userName"],
            "email": input_["request"]["userAttributes"]["email"]
        }),
        "EventBusName": EVENT_BUS_NAME
    }

    return output


@tracer.capture_method
def send_event(event: dict):
    """
    Send event to EventBridge
    """

    eventbridge.put_events(Entries=[event])


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda handler
    """

    # Input event:
    # https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools-working-with-aws-lambda-triggers.html#cognito-user-pools-lambda-trigger-event-parameter-shared
    logger.debug({
        "message": "Input event",
        "event": event
    })

    # Never confirm users
    event["response"] = {
        "autoConfirmUser": False,
        "autoVerifyPhone": False,
        "autoVerifyEmail": False
    }

    # Only care about the ConfirmSignUp action
    # At the moment, the only other PostConfirmation event is 'PostConfirmation_ConfirmForgotPassword'
    if event["triggerSource"] not in ["PreSignUp_SignUp", "PreSignUp_AdminCreateUser"]:
        logger.warning({
            "message": "invalid triggerSource",
            "triggerSource": event["triggerSource"]
        })
        return event

    # Prepare the event
    eb_event = process_request(event)

    # Send the event to EventBridge
    send_event(eb_event)

    # Always return the event at the end
    return event
