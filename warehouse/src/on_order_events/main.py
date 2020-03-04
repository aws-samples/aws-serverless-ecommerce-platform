"""
OrderEventsFunction
"""


import os
from typing import Dict, List, Optional
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context
import boto3
from boto3.dynamodb.conditions import Key


ENVIRONMENT = os.environ["ENVIRONMENT"]
METADATA_KEY = os.environ["METADATA_KEY"]
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = logger_setup() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def get_diff(old_products: List[dict], new_products: List[dict]) -> Dict[str, dict]:
    """
    Returns the difference between two lists of products

    The difference contains three possible keys: 'created', 'deleted' or 'modified'.
    """

    # Transform lists into dict
    old = {p["productId"]: p for p in old_products}
    new = {p["productId"]: p for p in new_products}

    diff = {
        "created": [],
        "deleted": [],
        "modified": []
    }

    for product_id, product in new.items():
        if product_id not in old:
            diff["created"].append(product)
            continue

        if product != old[product_id]:
            # As DynamoDB put_item operations overwrite the whole item, we
            # don't need to save the old item.
            diff["modified"].append(product)

        # Remove the item from old
        del old[product_id]

    # Since we delete values from 'old' as we encounter them, only values that
    # are in 'old' but not in 'new' are left. Therefore, these were deleted
    # from the original order.
    diff["deleted"] = list(old.values())

    return diff


@tracer.capture_method
def get_metadata(order_id: str) -> Optional[dict]:
    """
    Retrieve metadata for an order
    """

    res = table.get_item(Key={
        "orderId": order_id,
        "productId": METADATA_KEY
    })

    return res.get("Item", None)


@tracer.capture_method
def get_products(order_id: str) -> List[dict]:
    """
    Retrieve products from the DynamoDB table
    """

    res = table.query(
        KeyConditionExpression=Key("orderId").eq(order_id),
        Limit=100
    )
    logger.info({
        "message": "Retrieving {} products from order {}".format(
            len(res.get("Items", [])), order_id
        ),
        "operation": "query",
        "orderId": order_id
    })
    products = res.get("Items", [])

    while res.get("LastEvaluatedKey", None) is not None:
        res = table.query(
            KeyConditionExpression=Key("orderId").eq(order_id),
            ExclusiveStartKey=res["LastEvaluatedKey"],
            Limit=100
        )
        logger.info({
            "message": "Retrieving {} products from order {}".format(
                len(res.get("Items", [])), order_id
            ),
            "operation": "query",
            "orderId": order_id
        })
        products.extend(res.get("Items", []))

    return products


@tracer.capture_method
def delete_metadata(order_id: str):
    """
    Delete order metadata from the DynamoDB table
    """

    table.delete_item(Key={
        "orderId": order_id,
        "productId": METADATA_KEY
    })


@tracer.capture_method
def delete_products(order_id: str, products: Optional[list] = None) -> None:
    """
    Delete products from the DynamoDB table
    """

    count = 0
    with table.batch_writer() as batch:
        # If no list of 'products' is specified, deleted all products for
        # that item.
        for product in products or get_products(order_id):
            # Skip metadata key
            if product["productId"] == METADATA_KEY:
                continue

            count += 1
            batch.delete_item(Key={
                "orderId": order_id,
                "productId": product["productId"]
            })
            logger.debug({
                "message": "Deleting product {} for order {}".format(
                    product["productId"], order_id
                ),
                "operation": "delete",
                "product": product,
                "orderId": order_id
            })

    logger.info({
        "message": "Deleting {} products for order {}".format(
            count, order_id
        ),
        "operation": "delete",
        "orderId": order_id,
        "productCount": count
    })


@tracer.capture_method
def save_metadata(order_id: str, modified_date: str, status: str = "NEW") -> None:
    """
    Save metadata in the DynamoDB table
    """

    item = {
        "orderId": order_id,
        "productId": METADATA_KEY,
        "modifiedDate": modified_date,
        "status": status
    }

    table.put_item(Item=item)


@tracer.capture_method
def save_products(order_id: str, products: List[dict]) -> None:
    """
    Save products in the DynamoDB table
    """

    logger.info({
        "message": "Writing {} products for order {}".format(
            len(products), order_id
        ),
        "operation": "put",
        "orderId": order_id,
        "productCount": len(products)
    })

    with table.batch_writer() as batch:
        for product in products:
            item = {
                "orderId": order_id,
                "productId": product["productId"],
                "quantity": product.get("quantity", 1)
            }
            logger.debug({
                "message": "Writing product {}".format(product["productId"]),
                "operation": "put",
                "product": item,
                "orderId": order_id
            })
            batch.put_item(Item=item)


@tracer.capture_method
def update_products(order_id: str, old_products: List[dict], new_products: List[dict]):
    """
    Update products in DynamoDB
    """

    diff = get_diff(old_products, new_products)

    # As DynamoDB put_item overwrite existing items, we can perform both steps
    # in one go.
    if len(diff["created"]) + len(diff["modified"]) > 0:
        save_products(order_id, diff["created"] + diff["modified"])

    if len(diff["deleted"]) > 0:
        delete_products(order_id, diff["deleted"])


@tracer.capture_method
def on_order_created(order: dict):
    """
    Process an OrderCreated event
    """

    order_id = order["orderId"]

    # Idempotency check
    metadata = get_metadata(order_id)
    # Check if the metadata exist and is newer/same version as the event
    if metadata is not None and metadata["modifiedDate"] >= order["modifiedDate"]:
        logger.info({
            "message": "Order {} is already in the database".format(order_id),
            "orderId": order_id
        })
        # Skipping
        return

    save_products(order_id, order["products"])
    save_metadata(order_id, order["modifiedDate"])


@tracer.capture_method
def on_order_modified(old_order: dict, new_order: dict):
    """
    Process an OrderModified event
    """

    order_id = old_order["orderId"]

    # Idempotency check
    metadata = get_metadata(order_id)
    # If no metadata, the order is not in the database
    if metadata is None:
        save_products(order_id, new_order["products"])
        save_metadata(order_id, new_order["modifiedDate"])
    # Accepting modifications only if the order is in the 'NEW' state and
    # the event is newer than the last known state
    elif metadata["status"] == "NEW" and metadata["modifiedDate"] < new_order["modifiedDate"]:
        update_products(old_order["orderId"], old_order["products"], new_order["products"])
        save_metadata(old_order["orderId"], new_order["modifiedDate"], metadata["status"])


@tracer.capture_method
def on_order_deleted(order: dict):
    """
    Process an OrderDeleted event
    """

    order_id = order["orderId"]

    # Idempotency check
    metadata = get_metadata(order_id)
    # If no metadata, the order is not in the database.
    # If the order status is not 'NEW', we cannot cancel the order.
    if metadata is None or metadata["status"] != "NEW":
        return

    delete_products(order_id, order["products"])
    delete_metadata(order_id)


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler for OrderEvents
    """

    if event["detail-type"] == "OrderCreated":
        on_order_created(event["detail"])
    elif event["detail-type"] == "OrderDeleted":
        on_order_deleted(event["detail"])
    elif event["detail-type"] == "OrderModified":
        on_order_modified(event["detail"]["old"], event["event"]["new"])
    else:
        logger.warning({
            "message": "Unkown detail-type {}".format(event["detail-type"]),
            "detailType": event["detail-type"]
        })
