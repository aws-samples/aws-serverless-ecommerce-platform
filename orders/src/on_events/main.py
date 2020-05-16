"""
OnPackageCreated Function
"""


import datetime
import json
import os
from typing import List, Optional, Union
import boto3
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging.logger import Logger # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = Logger() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def log_metrics(metric_names: Union[str, List[str]], metric_values: Union[int, List[int]]) -> None:
    """
    Log custom metrics
    """

    if isinstance(metric_names, str):
        metric_names = [metric_names]
    if isinstance(metric_values, int):
        metric_values = [metric_values]

    assert len(metric_names) <= len(metric_values)

    metrics = {metric_names[i]: metric_values[i] for i in range(len(metric_names))}
    metrics["environment"] = ENVIRONMENT
    metrics["_aws"] = {
        # Timestamp is in milliseconds
        "Timestamp": int(datetime.datetime.now().timestamp()*1000),
        "CloudWatchMetrics": [{
            "Namespace": "ecommerce.orders",
            "Dimensions": [["environment"]],
            "Metrics": [
                {"Name": name} for name in metric_names
            ]
        }]
    }

    print(json.dumps(metrics))


@tracer.capture_method
def update_order(order_id: str, status: str, products: Optional[List[dict]] = None) -> None:
    """
    Update packages in the order
    """

    logger.info({
        "message": "Update status for order {} to {}".format(order_id, status),
        "orderId": order_id,
        "status": status
    })

    update_expression = "set #s = :s"
    attribute_names = {
        "#s": "status"
    }
    attribute_values = {
        ":s": status
    }

    if products is not None:
        product_ids = [p["productId"] for p in products]

        item = table.get_item(
            Key={"orderId": order_id},
            AttributesToGet=["products"]
        )["Item"]
        new_products = []
        for product in item["products"]:
            if product["productId"] in product_ids:
                new_products.append(product)

        update_expression += ", #p = :p"
        attribute_names["#p"] = "products"
        attribute_values[":p"] = products


    table.update_item(
        Key={"orderId": order_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=attribute_names,
        ExpressionAttributeValues=attribute_values
    )


@logger.inject_lambda_context
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
        tracer.put_annotation("orderId", order_id)
        if event["source"] == "ecommerce.warehouse":
            if event["detail-type"] == "PackageCreated":
                log_metrics("orderPackaged", 1)
                update_order(order_id, "PACKAGED", event["detail"]["products"])
            elif event["detail-type"] == "PackagingFailed":
                log_metrics("orderFailed", 1)
                update_order(order_id, "PACKAGING_FAILED")
            else:
                logger.warning({
                    "message": "Unknown event type {} for order {}".format(event["detail-type"], order_id),
                    "source": event["source"],
                    "eventType": event["detail-type"],
                    "orderId": order_id
                })
        elif event["source"] == "ecommerce.delivery":
            if event["detail-type"] == "DeliveryCompleted":
                log_metrics("orderFulfilled", 1)
                update_order(order_id, "FULFILLED")
            elif event["detail-type"] == "DeliveryFailed":
                log_metrics("orderFailed", 1)
                update_order(order_id, "DELIVERY_FAILED")
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
