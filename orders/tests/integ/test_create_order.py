import copy
import json
import boto3
import pytest
import requests
from fixtures import iam_auth, get_order, get_product # pylint: disable=import-error,no-name-in-module
from helpers import compare_dict, get_parameter # pylint: disable=import-error,no-name-in-module


@pytest.fixture(scope="module")
def delivery_api_url():
    return get_parameter("/ecommerce/{Environment}/delivery-pricing/api/url")


@pytest.fixture(scope="module")
def payment_3p_api_url():
    return get_parameter("/ecommerce/{Environment}/payment-3p/api/url")


@pytest.fixture(scope="module")
def product_table_name():
    return get_parameter("/ecommerce/{Environment}/products/table/name")


@pytest.fixture(scope="module")
def table_name():
    return get_parameter("/ecommerce/{Environment}/orders/table/name")


@pytest.fixture(scope="module")
def function_arn():
    return get_parameter("/ecommerce/{Environment}/orders/create-order/arn")


@pytest.fixture(scope="function")
def order(get_order):
    return get_order()


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="function")
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


def test_create_order(function_arn, table_name, order_request):
    """
    Test the CreateOrder function
    """

    order_request = copy.deepcopy(order_request)

    table = boto3.resource("dynamodb").Table(table_name) #pylint: disable=no-member
    lambda_ = boto3.client("lambda")

    # Trigger the function
    response = lambda_.invoke(
        FunctionName=function_arn,
        InvocationType="RequestResponse",
        Payload=json.dumps(order_request).encode()
    )
    response = json.load(response["Payload"])

    print(response)

    # Check the output of the Function
    assert response["success"] == True
    assert "order" in response
    assert len(response.get("errors", [])) == 0

    del order_request["order"]["products"]
    compare_dict(order_request["order"], response["order"])
    assert response["order"]["userId"] == order_request["userId"]

    # Check the table
    ddb_response = table.get_item(Key={"orderId": response["order"]["orderId"]})
    assert "Item" in ddb_response

    mandatory_fields = [
        "orderId", "userId", "createdDate", "modifiedDate", "status",
        "products", "address", "deliveryPrice", "total"
    ]
    for field in mandatory_fields:
        assert field in ddb_response["Item"]

    assert ddb_response["Item"]["status"] == "NEW"

    compare_dict(order_request["order"], ddb_response["Item"])

    # Cleanup the table
    table.delete_item(Key={"orderId": response["order"]["orderId"]})


def test_create_order_fail_products(function_arn, table_name, order_request, get_product):
    """
    Test the CreateOrder function
    """

    order_request = copy.deepcopy(order_request)
    order_request["order"]["products"] = [get_product()]

    lambda_ = boto3.client("lambda")

    # Trigger the function
    response = lambda_.invoke(
        FunctionName=function_arn,
        InvocationType="RequestResponse",
        Payload=json.dumps(order_request).encode()
    )
    response = json.load(response["Payload"])

    print(response)

    # Check the output of the Function
    assert response["success"] == False
    assert len(response.get("errors", [])) > 0


def test_create_order_fail_delivery_price(function_arn, table_name, order_request, get_product):
    """
    Test the CreateOrder function
    """

    order_request = copy.deepcopy(order_request)
    order_request["order"]["deliveryPrice"] += 200

    lambda_ = boto3.client("lambda")

    # Trigger the function
    response = lambda_.invoke(
        FunctionName=function_arn,
        InvocationType="RequestResponse",
        Payload=json.dumps(order_request).encode()
    )
    response = json.load(response["Payload"])

    print(response)

    # Check the output of the Function
    assert response["success"] == False
    assert len(response.get("errors", [])) > 0