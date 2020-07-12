import copy
import json
import time
import datetime
import boto3
from boto3.dynamodb.conditions import Key
import pytest
import requests
from fixtures import iam_auth, get_order, get_product # pylint: disable=import-error
from helpers import get_parameter # pylint: disable=import-error,no-name-in-module


@pytest.fixture(scope="module")
def delivery_table_name():
    """
    DynamoDB table name
    """

    return get_parameter("/ecommerce/{Environment}/delivery/table/name")


@pytest.fixture(scope="module")
def product_table_name():
    return get_parameter("/ecommerce/{Environment}/products/table/name")


@pytest.fixture(scope="module")
def event_bus_name():
    """
    Event Bus name
    """

    return get_parameter("/ecommerce/{Environment}/platform/event-bus/name")


@pytest.fixture(scope="module")
def delivery_api_url():
    return get_parameter("/ecommerce/{Environment}/delivery-pricing/api/url")


@pytest.fixture(scope="module")
def payment_3p_api_url():
    return get_parameter("/ecommerce/{Environment}/payment-3p/api/url")


@pytest.fixture(scope="module")
def function_arn():
    return get_parameter("/ecommerce/{Environment}/orders/create-order/arn")


@pytest.fixture
def order(get_order):
    return get_order()


@pytest.fixture
def products(product_table_name, get_product):
    """
    Create fake products
    """

    table = boto3.resource("dynamodb").Table(product_table_name) # pylint: disable=no-member

    products = [get_product() for _ in range(3)]

    for product in products:
        table.put_item(Item=product)

    yield products

    for product in products:
        table.delete_item(Key={"productId": product["productId"]})


@pytest.fixture
def delivery_price(delivery_api_url, iam_auth, order, products):
    res = requests.post(
        url=delivery_api_url+"/backend/pricing",
        auth=iam_auth(delivery_api_url),
        json={
            "products": products,
            "address": order["address"]
        }
    )

    body = res.json()
    print(body)

    return body["pricing"]


@pytest.fixture
def payment_token(payment_3p_api_url, delivery_price, products):

    # Calculate the order total
    amount = sum([p["price"]*p.get("quantity", 1) for p in products]) + delivery_price

    # Generate a payment token
    res = requests.post(payment_3p_api_url+"/preauth", json={
        "cardNumber": "1234567890123456",
        "amount": amount
    })

    payment_token = res.json()["paymentToken"]
    yield payment_token

    # Cancel the payment token
    requests.post(payment_3p_api_url+"/cancelPayment", json={
        "paymentToken": payment_token
    })


@pytest.fixture
def order_request(order, products, delivery_price, payment_token):

    return {
        "userId": order["userId"],
        "order": {
            "products": products,
            "address": order["address"],
            "deliveryPrice": delivery_price,
            "paymentToken": payment_token
        }
    }


def test_on_package_created(function_arn, delivery_table_name, order_request, event_bus_name):

    """
    Use the CreateOrder function to create an order which triggers the ecommerce flow
    """

    order_request = copy.deepcopy(order_request)

    lambda_ = boto3.client("lambda")

    # Trigger the function
    response = lambda_.invoke(
        FunctionName=function_arn,
        InvocationType="RequestResponse",
        Payload=json.dumps(order_request).encode()
    )
    response = json.load(response["Payload"])

    # Check the output of the Function
    assert response["success"] == True
    assert "order" in response
    assert len(response.get("errors", [])) == 0

    order = response["order"]

    eventbridge = boto3.client("events")

    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.warehouse",
        "Resources": [order["orderId"]],
        "DetailType": "PackageCreated",
        "Detail": json.dumps(order),
        "EventBusName": event_bus_name
    }

    # Send the event on EventBridge
    eventbridge.put_events(Entries=[event])

    # Wait
    time.sleep(5)

    table = boto3.resource("dynamodb").Table(delivery_table_name)  # pylint: disable=no-member

    # Check DynamoDB
    results = table.query(
        KeyConditionExpression=Key("orderId").eq(order["orderId"])
    )

    # Assertions that a new package for delivery exists
    package = results.get("Items", [])
    assert len(package) == 1
    assert package[0]['isNew'] == 'true'
    assert package[0]['status'] == 'NEW'
