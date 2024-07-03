import copy
import datetime
import random
import uuid
from botocore import stub
import pytest
from fixtures import context, lambda_module, get_order, get_product # pylint: disable=import-error
from helpers import mock_table # pylint: disable=import-error,no-name-in-module


METADATA_KEY = "__metadata"


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "on_order_events",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "METADATA_KEY": METADATA_KEY,
        "TABLE_NAME": "TABLE_NAME",
        "ORDERS_LIMIT": "20",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


@pytest.fixture(scope="module")
def order(get_order):
    return get_order()


@pytest.fixture()
def order_metadata(order):
    return {
        "orderId": order["orderId"],
        "productId": METADATA_KEY,
        "modifiedDate": order["modifiedDate"],
        "status": "NEW"
    }


@pytest.fixture
def order_products(order):
    return [
        {
            "orderId": order["orderId"],
            "productId": product["productId"],
            "quantity": product["quantity"]
        }
        for product in order["products"]
    ]


def test_get_diff(lambda_module, get_product):
    """
    Test get_diff()
    """

    def _get_product():
        product = get_product()
        product["quantity"] = random.randint(1, 10)
        return product

    old_products = [_get_product() for _ in range(5)]
    new_products = copy.deepcopy(old_products[1:]) + [_get_product()]
    new_products[0]["quantity"] += 10

    response = lambda_module.get_diff(old_products, new_products)

    assert "created" in response
    assert len(response["created"]) == 1
    assert response["created"][0] == new_products[-1]

    assert "deleted" in response
    assert len(response["deleted"]) == 1
    assert response["deleted"][0] == old_products[0]

    assert "modified" in response
    assert len(response["modified"]) == 1
    assert response["modified"][0] == new_products[0]


def test_get_metadata(lambda_module, order_metadata):
    """
    Test get_metadata()
    """

    table = mock_table(
        lambda_module.table, "get_item",
        ["orderId", "productId"],
        items=order_metadata
    )

    response = lambda_module.get_metadata(order_metadata["orderId"])

    table.assert_no_pending_responses()
    table.deactivate()

    assert response == order_metadata


def test_get_products(lambda_module, order, order_products):
    """
    Test get_products()
    """

    table = mock_table(
        lambda_module.table, "query",
        ["orderId", "productId"],
        items=order_products
    )

    response = lambda_module.get_products(order["orderId"])

    table.assert_no_pending_responses()
    table.deactivate()

    assert response == order_products


def test_get_products_next(lambda_module, order, order_products):
    """
    Test get_products() with a LastEvaluatedKey value
    """

    table = mock_table(
        lambda_module.table, "query",
        ["orderId", "productId"],
        response={
            "Items": order_products,
            "LastEvaluatedKey": {
                "orderId": {"S": order_products[-1]["orderId"]},
                "productId": {"S": order_products[-1]["productId"]}
            }
        },
        items=order_products
    )
    mock_table(
        table, "query",
        ["orderId", "productId"],
        expected_params={
            "TableName": lambda_module.table.name,
            "KeyConditionExpression": stub.ANY,
            "Limit": 100,
            "ExclusiveStartKey": {
                "orderId": order_products[-1]["orderId"],
                "productId": order_products[-1]["productId"]
            }
        },
        items=order_products
    )

    response = lambda_module.get_products(order["orderId"])

    table.assert_no_pending_responses()
    table.deactivate()

    assert response == order_products + order_products


def test_delete_metadata(lambda_module, order_metadata):
    """
    Test delete_metadata()
    """

    table = mock_table(
        lambda_module.table, "delete_item",
        ["orderId", "productId"],
        items=order_metadata
    )

    lambda_module.delete_metadata(order_metadata["orderId"])

    table.assert_no_pending_responses()
    table.deactivate()


def test_delete_products(lambda_module, order, order_products):
    """
    Test delete_products()
    """

    table = mock_table(
        lambda_module.table, "batch_write_item",
        ["orderId", "productId"],
        items=[
            {"DeleteRequest": {"Key": {
                "orderId": product["orderId"],
                "productId": product["productId"]
            }}}
            for product in order_products
        ]
    )

    products = order["products"] + [{"orderId": order["orderId"], "productId": METADATA_KEY}]

    lambda_module.delete_products(order["orderId"], products)

    table.assert_no_pending_responses()
    table.deactivate()


def test_save_metadata(lambda_module, order_metadata):
    """
    Test save_metadata()
    """

    item = copy.deepcopy(order_metadata)
    item["newDate"] = order_metadata["modifiedDate"]

    table = mock_table(
        lambda_module.table, "put_item",
        ["orderId", "productId"],
        items=item
    )

    lambda_module.save_metadata(
        order_metadata["orderId"],
        order_metadata["modifiedDate"],
        order_metadata["status"]
    )

    table.assert_no_pending_responses()
    table.deactivate()


def test_save_products(lambda_module, order, order_products):
    """
    Test save_products()
    """

    table = mock_table(
        lambda_module.table, "batch_write_item",
        ["orderId", "productId"],
        items=[
            {"PutRequest": {"Item": product}}
            for product in order_products
        ]
    )

    lambda_module.save_products(order["orderId"], order["products"])

    table.assert_no_pending_responses()
    table.deactivate()


def test_update_products_new(lambda_module, order, order_products):
    """
    Test update_products() with new products only
    """

    table = mock_table(
        lambda_module.table, "batch_write_item",
        ["orderId", "productId"],
        items=[
            {"PutRequest": {"Item": product}}
            for product in order_products
        ]
    )

    lambda_module.update_products(order["orderId"], [], order["products"])

    table.assert_no_pending_responses()
    table.deactivate()


def test_update_products_old(lambda_module, order, order_products):
    """
    Test update_products() with old products only
    """

    table = mock_table(
        lambda_module.table, "batch_write_item",
        ["orderId", "productId"],
        items=[
            {"DeleteRequest": {"Key": {
                "orderId": product["orderId"],
                "productId": product["productId"]
            }}}
            for product in order_products
        ]
    )

    lambda_module.update_products(order["orderId"], order["products"], [])

    table.assert_no_pending_responses()
    table.deactivate()


def test_on_order_created(lambda_module, order, order_products, order_metadata):
    """
    Test on_order_created()
    """

    table = mock_table(
        lambda_module.table, "get_item", ["orderId", "productId"]
    )
    mock_table(
        table, "batch_write_item",
        ["orderId", "productId"],
        table_name=lambda_module.table.name,
        items=[
            {"PutRequest": {"Item": product}}
            for product in order_products
        ]
    )
    order_metadata = copy.deepcopy(order_metadata)
    order_metadata["newDate"] = order_metadata["modifiedDate"]
    mock_table(
        table, "put_item", ["orderId", "productId"],
        table_name=lambda_module.table.name,
        items=order_metadata
    )
    
    lambda_module.on_order_created(order)

    table.assert_no_pending_responses()
    table.deactivate()


def test_on_order_created_idempotent(lambda_module, order, order_metadata):
    """
    Test on_order_created() with an existing item
    """

    table = mock_table(
        lambda_module.table, "get_item", ["orderId", "productId"],
        items=order_metadata
    )
    
    lambda_module.on_order_created(order)

    table.assert_no_pending_responses()
    table.deactivate()


def test_on_order_modified_new(lambda_module, order, order_products, order_metadata):
    """
    Test on_order_modified() with a new event
    """

    table = mock_table(
        lambda_module.table, "get_item", ["orderId", "productId"]
    )
    mock_table(
        table, "batch_write_item",
        ["orderId", "productId"],
        table_name=lambda_module.table.name,
        items=[
            {"PutRequest": {"Item": product}}
            for product in order_products
        ]
    )
    order_metadata = copy.deepcopy(order_metadata)
    order_metadata["newDate"] = order_metadata["modifiedDate"]
    mock_table(
        table, "put_item", ["orderId", "productId"],
        table_name=lambda_module.table.name,
        items=order_metadata
    )

    lambda_module.on_order_modified(order, order)

    table.assert_no_pending_responses()
    table.deactivate()


def test_on_order_modified_idempotent(lambda_module, order, order_metadata):
    """
    Test on_order_modified() with an already processed event
    """

    table = mock_table(
        lambda_module.table, "get_item", ["orderId", "productId"],
        items=order_metadata
    )

    lambda_module.on_order_modified(order, order)

    table.assert_no_pending_responses()
    table.deactivate()


def test_on_order_deleted(lambda_module, order, order_products, order_metadata):
    """
    Test on_order_deleted()
    """

    table = mock_table(
        lambda_module.table, "get_item", ["orderId", "productId"],
        items=order_metadata
    )
    mock_table(
        table, "batch_write_item",
        ["orderId", "productId"],
        table_name=lambda_module.table.name,
        items=[
            {"DeleteRequest": {"Key": {
                "orderId": product["orderId"],
                "productId": product["productId"]
            }}}
            for product in order_products
        ]
    )
    mock_table(
        table, "delete_item",
        ["orderId", "productId"],
        table_name=lambda_module.table.name,
        items=order_metadata
    )
    
    lambda_module.on_order_deleted(order)

    table.assert_no_pending_responses()
    table.deactivate()


def test_on_order_deleted_idempotent(lambda_module, order):
    """
    Test on_order_deleted() with an already deleted item
    """

    table = mock_table(
        lambda_module.table, "get_item", ["orderId", "productId"]
    )
    
    lambda_module.on_order_deleted(order)

    table.assert_no_pending_responses()
    table.deactivate()


def test_handler_created(lambda_module, context, order, order_products, order_metadata):
    """
    Test handler() with OrderCreated
    """

    table = mock_table(
        lambda_module.table, "get_item", ["orderId", "productId"]
    )
    mock_table(
        table, "batch_write_item",
        ["orderId", "productId"],
        table_name=lambda_module.table.name,
        items=[
            {"PutRequest": {"Item": product}}
            for product in order_products
        ]
    )
    order_metadata = copy.deepcopy(order_metadata)
    order_metadata["newDate"] = order_metadata["modifiedDate"]
    mock_table(
        table, "put_item", ["orderId", "productId"],
        table_name=lambda_module.table.name,
        items=order_metadata
    )

    lambda_module.handler({
        "source": "ecommerce.orders",
        "resources": [order["orderId"]],
        "detail-type": "OrderCreated",
        "detail": order
    }, context)

    table.assert_no_pending_responses()
    table.deactivate()


def test_handler_deleted(lambda_module, context, order, order_products, order_metadata):
    """
    Test handler() with OrderDeleted
    """

    table = mock_table(
        lambda_module.table, "get_item", ["orderId", "productId"],
        items=order_metadata
    )
    mock_table(
        table, "batch_write_item",
        ["orderId", "productId"],
        table_name=lambda_module.table.name,
        items=[
            {"DeleteRequest": {"Key": {
                "orderId": product["orderId"],
                "productId": product["productId"]
            }}}
            for product in order_products
        ]
    )
    mock_table(
        table, "delete_item",
        ["orderId", "productId"],
        table_name=lambda_module.table.name,
        items=order_metadata
    )

    lambda_module.handler({
        "source": "ecommerce.orders",
        "resources": [order["orderId"]],
        "detail-type": "OrderDeleted",
        "detail": order
    }, context)

    table.assert_no_pending_responses()
    table.deactivate()