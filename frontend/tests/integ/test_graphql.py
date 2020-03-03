import pytest
import requests
import boto3
from fixtures import get_product # pylint: disable=import-error,no-name-in-module
from helpers import get_parameter # pylint: disable=import-error,no-name-in-module


@pytest.fixture
def products_table_name():
    """
    Products DynamoDB table name
    """

    return get_parameter("/ecommerce/{Environment}/products/table/name")


@pytest.fixture
def orders_table_name():
    """
    Orders DynamoDB table name
    """

    return get_parameter("/ecommerce/{Environment}/orders/table/name")


@pytest.fixture
def api_id():
    """
    Frontend GraphQL API ID
    """

    return get_parameter("/ecommerce/{Environment}/frontend/api/id")


@pytest.fixture
def api_url():
    """
    Frontend GraphQL API URL
    """

    return get_parameter("/ecommerce/{Environment}/frontend/api/url")


@pytest.fixture
def api_key(api_id):
    """
    API Key for AppSync
    """

    appsync = boto3.client("appsync")
    response = appsync.create_api_key(apiId=api_id)

    yield response["apiKey"]["id"]

    appsync.delete_api_key(apiId=api_id, id=response["apiKey"]["id"])


@pytest.fixture(scope="function")
def product(get_product, products_table_name):
    """
    Product
    """
    table = boto3.resource("dynamodb").Table(products_table_name) # pylint: disable=no-member
    product = get_product()

    table.put_item(Item=product)

    yield product

    table.delete_item(Key={"productId": product["productId"]})


def test_get_products(api_url, product, api_key):
    """
    Test getProducts
    """

    headers = {"X-Api-Key": api_key}

    query = """
    query {
      getProducts {
        products {
          productId
          name
        }
      }
    }
    """

    response = requests.post(api_url, json={"query": query}, headers=headers)

    data = response.json()

    assert "data" in data
    assert "getProducts" in data["data"]
    assert "products" in data["data"]["getProducts"]

    found = False
    for res_product in data["data"]["getProducts"]["products"]:
        if res_product["productId"] == product["productId"]:
            found = True
    assert found == True