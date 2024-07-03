import copy
import datetime
import json
import time
import uuid
import boto3
import pytest
import requests
from fixtures import get_order, get_product # pylint: disable=import-error
from helpers import get_parameter # pylint: disable=import-error,no-name-in-module


@pytest.fixture(scope="module")
def payment_3p_api_url():
    return get_parameter("/ecommerce/{Environment}/payment-3p/api/url")


@pytest.fixture(scope="module")
def event_bus_name():
    return get_parameter("/ecommerce/{Environment}/platform/event-bus/name")


@pytest.fixture(scope="module")
def table():
    table_name = get_parameter("/ecommerce/{Environment}/payment/table/name")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name) # pylint: disable=no-member


@pytest.fixture(scope="module")
def eventbridge():
    return boto3.client("events")


@pytest.fixture(scope="module")
def order(get_order):
    return get_order()


def test_on_created(eventbridge, event_bus_name, table, order):
    """
    Test OnCreated
    """

    # Put the event
    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.orders",
        "Resources": [order["orderId"]],
        "DetailType": "OrderCreated",
        "Detail": json.dumps(order),
        "EventBusName": event_bus_name
    }
    eventbridge.put_events(Entries=[event])

    # Wait
    time.sleep(5)

    # Check Dynamodb
    res = table.get_item(Key={"orderId": order["orderId"]})

    assert "Item" in res
    assert "orderId" in res["Item"]
    assert "paymentToken" in res["Item"]
    assert res["Item"]["orderId"] == order["orderId"]
    assert res["Item"]["paymentToken"] == order["paymentToken"]

    # Clean up
    table.delete_item(Key={"orderId": order["orderId"]})


def test_on_modified(payment_3p_api_url, eventbridge, event_bus_name, table, order):
    """
    Test OnModified
    """

    total = 3000
    new_total = 2000

    # Create paymentToken
    res_3p = requests.post(payment_3p_api_url+"/preauth", json={
        "cardNumber": "1234567890123456",
        "amount": total
    })
    payment_token = res_3p.json()["paymentToken"]

    # Create order
    order = copy.deepcopy(order)
    order["paymentToken"] = payment_token
    new_order = copy.deepcopy(order)
    new_order["paymentToken"] = payment_token
    new_order["total"] = new_total

    # Store in DynamoDB
    table.put_item(Item={
        "orderId": order["orderId"],
        "paymentToken": payment_token
    })

    # Put the event
    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.orders",
        "Resources": [order["orderId"]],
        "DetailType": "OrderModified",
        "Detail": json.dumps({
            "old": order,
            "new": new_order,
            "changed": ["total"]
        }),
        "EventBusName": event_bus_name
    }
    eventbridge.put_events(Entries=[event])

    # Wait
    time.sleep(5)

    # Check values

    # Original value
    res_3p = requests.post(payment_3p_api_url+"/check", json={
        "paymentToken": payment_token,
        "amount": total
    })
    assert res_3p.json()["ok"] == False

    # New value + 1
    res_3p = requests.post(payment_3p_api_url+"/check", json={
        "paymentToken": payment_token,
        "amount": new_total+1
    })
    assert res_3p.json()["ok"] == False

    # New value
    res_3p = requests.post(payment_3p_api_url+"/check", json={
        "paymentToken": payment_token,
        "amount": new_total
    })
    assert res_3p.json()["ok"] == True

    # Cleanup
    # requests.post(payment_3p_api_url+"/cancelPayment", json={
    #     "paymentToken": payment_token
    # })


def test_on_failed_warehouse(payment_3p_api_url, eventbridge, event_bus_name, table, order):
    """
    Test OnFailed from warehouse
    """

    total = 3000

    # Create paymentToken
    res_3p = requests.post(payment_3p_api_url+"/preauth", json={
        "cardNumber": "1234567890123456",
        "amount": total
    })
    payment_token = res_3p.json()["paymentToken"]

    # Create order
    order = copy.deepcopy(order)
    order["paymentToken"] = payment_token
    new_order = copy.deepcopy(order)
    new_order["paymentToken"] = payment_token
    new_order["total"] = total

    # Store in DynamoDB
    table.put_item(Item={
        "orderId": order["orderId"],
        "paymentToken": payment_token
    })

    # Put the event
    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.warehouse",
        "Resources": [order["orderId"]],
        "DetailType": "PackagingFailed",
        "Detail": json.dumps(order),
        "EventBusName": event_bus_name
    }
    eventbridge.put_events(Entries=[event])

    # Wait
    time.sleep(5)

    # Check DynamoDB
    res = table.get_item(Key={"orderId": order["orderId"]})
    assert "Item" not in res

    # Check 3rd party system
    res_3p = requests.post(payment_3p_api_url+"/check", json={
        "paymentToken": payment_token,
        "amount": total
    })
    assert res_3p.json()["ok"] == False
    res_3p = requests.post(payment_3p_api_url+"/check", json={
        "paymentToken": payment_token,
        "amount": 1
    })
    assert res_3p.json()["ok"] == False

def test_on_failed_delivery(payment_3p_api_url, eventbridge, event_bus_name, table, order):
    """
    Test OnFailed from delivery
    """

    total = 3000

    # Create paymentToken
    res_3p = requests.post(payment_3p_api_url+"/preauth", json={
        "cardNumber": "1234567890123456",
        "amount": total
    })
    payment_token = res_3p.json()["paymentToken"]

    # Create order
    order = copy.deepcopy(order)
    order["paymentToken"] = payment_token
    new_order = copy.deepcopy(order)
    new_order["paymentToken"] = payment_token
    new_order["total"] = total

    # Store in DynamoDB
    table.put_item(Item={
        "orderId": order["orderId"],
        "paymentToken": payment_token
    })

    # Put the event
    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.delivery",
        "Resources": [order["orderId"]],
        "DetailType": "DeliveryFailed",
        "Detail": json.dumps(order),
        "EventBusName": event_bus_name
    }
    eventbridge.put_events(Entries=[event])

    # Wait
    time.sleep(5)

    # Check DynamoDB
    res = table.get_item(Key={"orderId": order["orderId"]})
    assert "Item" not in res

    # Check 3rd party system
    res_3p = requests.post(payment_3p_api_url+"/check", json={
        "paymentToken": payment_token,
        "amount": total
    })
    assert res_3p.json()["ok"] == False
    res_3p = requests.post(payment_3p_api_url+"/check", json={
        "paymentToken": payment_token,
        "amount": 1
    })
    assert res_3p.json()["ok"] == False

def test_on_completed(payment_3p_api_url, eventbridge, event_bus_name, table, order):
    """
    Test OnCompleted
    """

    total = 3000

    # Create paymentToken
    res_3p = requests.post(payment_3p_api_url+"/preauth", json={
        "cardNumber": "1234567890123456",
        "amount": total
    })
    payment_token = res_3p.json()["paymentToken"]

    # Create order
    order = copy.deepcopy(order)
    order["paymentToken"] = payment_token
    new_order = copy.deepcopy(order)
    new_order["paymentToken"] = payment_token
    new_order["total"] = total

    # Store in DynamoDB
    table.put_item(Item={
        "orderId": order["orderId"],
        "paymentToken": payment_token
    })

    # Put the event
    event = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.delivery",
        "Resources": [order["orderId"]],
        "DetailType": "DeliveryCompleted",
        "Detail": json.dumps(order),
        "EventBusName": event_bus_name
    }
    eventbridge.put_events(Entries=[event])

    # Wait
    time.sleep(5)

    # Check DynamoDB
    res = table.get_item(Key={"orderId": order["orderId"]})
    assert "Item" not in res

    # Check 3rd party system
    res_3p = requests.post(payment_3p_api_url+"/check", json={
        "paymentToken": payment_token,
        "amount": total
    })
    assert res_3p.json()["ok"] == False
    res_3p = requests.post(payment_3p_api_url+"/check", json={
        "paymentToken": payment_token,
        "amount": 1
    })
    assert res_3p.json()["ok"] == False