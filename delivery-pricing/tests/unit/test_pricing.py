import json
import math
from typing import List
import pytest
from fixtures import apigateway_event, context, lambda_module, get_order, get_product # pylint: disable=import-error


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "pricing",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "TABLE_NAME": "TABLE_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


@pytest.fixture(scope="function", params=range(10))
def order(get_order):
    """
    Generate orders
    """
    return get_order()


def test_count_boxes(monkeypatch, lambda_module, order):
    """
    Test count_boxes()
    """

    monkeypatch.setattr(lambda_module, "BOX_VOLUME", 500*500*500)
    monkeypatch.setattr(lambda_module, "BOX_WEIGHT", 10000)

    packages = [p["package"] for p in order["products"]]

    volume = sum([p["width"]*p["length"]*p["height"] for p in packages])
    weight = sum([p["weight"] for p in packages])

    expected = max(math.ceil(volume/lambda_module.BOX_VOLUME), math.ceil(weight/lambda_module.BOX_WEIGHT))

    retval = lambda_module.count_boxes(packages)

    assert expected == retval


def test_get_shipping_cost(monkeypatch, lambda_module, order):
    """
    Test get_shipping_cost()
    """

    monkeypatch.setattr(lambda_module, "COUNTRY_SHIPPING_FEES", {
        order["address"]["country"]: 1000,
        "*": 2500
    })

    retval = lambda_module.get_shipping_cost(order["address"])

    assert retval == 1000


def test_get_pricing(monkeypatch, lambda_module, order):
    """
    Test get_pricing()
    """

    def count_boxes(packages: List[dict]) -> int:
        assert packages == [p["package"] for p in order["products"]]
        return 10

    def get_shipping_cost(address: dict) -> int:
        assert address == order["address"]
        return 14

    monkeypatch.setattr(lambda_module, "count_boxes", count_boxes)
    monkeypatch.setattr(lambda_module, "get_shipping_cost", get_shipping_cost)

    retval = lambda_module.get_pricing(order["products"], order["address"])

    assert retval == 140


def test_handler(monkeypatch, lambda_module, context, apigateway_event, order):
    """
    Test handler()
    """

    event = apigateway_event(
        iam="USER_ARN",
        body=json.dumps({"products": order["products"], "address": order["address"]})
    )

    def get_pricing(products: List[dict], address: dict) -> int:
        assert products == order["products"]
        assert address == order["address"]

        return 1000

    monkeypatch.setattr(lambda_module, "get_pricing", get_pricing)

    retval = lambda_module.handler(event, context)

    assert "statusCode" in retval
    assert retval["statusCode"] == 200
    assert "body" in retval

    body = json.loads(retval["body"])
    assert "pricing" in body
    assert body["pricing"] == 1000


def test_handler_no_iam(lambda_module, context, apigateway_event, order):
    """
    Test handler() with no IAM credentials
    """

    event = apigateway_event(
        body=json.dumps({"products": order["products"], "address": order["address"]})
    )

    retval = lambda_module.handler(event, context)

    assert "statusCode" in retval
    assert retval["statusCode"] == 403
    assert "body" in retval
    body = json.loads(retval["body"])
    assert "message" in body

def test_handler_no_products(lambda_module, context, apigateway_event, order):
    """
    Test handler() with no IAM credentials
    """

    event = apigateway_event(
        iam="USER_ARN",
        body=json.dumps({"address": order["address"]})
    )

    retval = lambda_module.handler(event, context)

    assert "statusCode" in retval
    assert retval["statusCode"] == 400
    assert "body" in retval
    body = json.loads(retval["body"])
    assert "message" in body

def test_handler_no_address(lambda_module, context, apigateway_event, order):
    """
    Test handler() with no IAM credentials
    """

    event = apigateway_event(
        iam="USER_ARN",
        body=json.dumps({"products": order["products"]})
    )

    retval = lambda_module.handler(event, context)

    assert "statusCode" in retval
    assert retval["statusCode"] == 400
    assert "body" in retval
    body = json.loads(retval["body"])
    assert "message" in body

def test_handler_invalid_json(lambda_module, context, apigateway_event, order):
    """
    Test handler() with no IAM credentials
    """

    event = apigateway_event(
        iam="USER_ARN",
        body=json.dumps({"products": order["products"], "address": order["address"]})+"}"
    )

    retval = lambda_module.handler(event, context)

    assert "statusCode" in retval
    assert retval["statusCode"] == 400
    assert "body" in retval
    body = json.loads(retval["body"])
    assert "message" in body