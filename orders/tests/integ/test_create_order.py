import copy
import json
import boto3
import pytest
from fixtures import get_order, get_product # pylint: disable=import-error,no-name-in-module
from helpers import compare_dict, get_parameter # pylint: disable=import-error,no-name-in-module


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


@pytest.fixture(scope="function")
def order_request(get_order, products):
    order = get_order()

    return {
        "userId": order["userId"],
        "order": {
            "products": products,
            "address": order["address"],
            "deliveryPrice": order["deliveryPrice"],
            "paymentToken": order["paymentToken"]
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

    compare_dict(order_request["order"], ddb_response["Item"])

    # Cleanup the table
    response = table.get_item(Key={"orderId": response["order"]["orderId"]})


def test_create_order_fail(function_arn, table_name, order_request, get_product):
    """
    Test the CreateOrder function
    """

    order_request = copy.deepcopy(order_request)
    order_request["order"]["products"] = [get_product()]

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
    assert response["success"] == False
    assert len(response.get("errors", [])) > 0