"""
OnPackageCreated Function
"""


import os
import boto3
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = logger_setup() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def set_status(order_id: str, status: str) -> None:
    """
    Set the status of the order
    """

    logger.info({
        "message": "Update status for order {} to {}".format(order_id, status),
        "orderId": order_id,
        "status": status
    })

    table.update_item(
        Key={"orderId": order_id},
        UpdateExpression="set #s = :s",
        ExpressionAttributeNames={
            "#s": "status"
        },
        ExpressionAttributeValues={
            ":s": status
        }
    )


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda handler
    """

    order_ids = event["resources"]

    for order_id in order_ids:
        logger.info({
            "message": "Got event of type {} from {} for order {}".format(order_id, event["source"], event["resources"]),
            "source": event["source"],
            "eventType": event["detail-type"],
            "orderId": order_id
        })
        if event["source"] == "ecommerce.warehouse":
            if event["detail-type"] == "PackageCreated":
                set_status(order_id, "PACKAGED")
            elif event["detail-type"] == "PackagingFailed":
                set_status(order_id, "PACKAGING_FAILED")
            else:
                logger.warning({
                    "message": "Unknown event type {} for order {}".format(event["detail-type"], order_id),
                    "source": event["source"],
                    "eventType": event["detail-type"],
                    "orderId": order_id
                })
        elif event["source"] == "ecommerce.delivery":
            if event["detail-type"] == "DeliveryCompleted":
                set_status(order_id, "FULFILLED")
            elif event["detail-type"] == "DeliveryFailed":
                set_status(order_id, "DELIVERY_FAILED")
            else:
                logger.warning({
                    "message": "Unknown event type {} for order {}".format(event["detail-type"], order_id),
                    "source": event["source"],
                    "eventType": event["detail-type"],
                    "orderId": order_id
                })
        else:
            logger.warning({
                "message": "Unknown source {} for order {}".format(event["source"], order_id),
                "source": event["source"],
                "eventType": event["detail-type"],
                "orderId": order_id
            })
