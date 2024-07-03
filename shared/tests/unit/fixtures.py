import datetime
import importlib
import os
import random
import string
import sys
from typing import List, Optional
import uuid
import pytest



@pytest.fixture()
def apigateway_event():
    """
    Return a base API Gateway
    """

    def _apigateway_event(
            resource: str = "/",
            path: str = "/",
            method: str = "GET",
            body: Optional[str] = None,
            iam: Optional[str] = None,
            cognito: Optional[str] = None,
            path_params: Optional[dict] = None,
            query_params: Optional[dict] = None
            ) -> dict:
        """
        API Gateway event generator
        """
        event = {
            "resource": resource,
            "path": path,
            "httpMethod": method,
            "headers": None,
            "multiValueHeaders": None,
            "queryStringParameters": None,
            "multiValueQueryStringParameters": None,
            "pathParameters": None,
            "stageVariables": None,
            "requestContext": None,
            "body": body,
            "isBase64Encoded": False
        }

        if cognito is not None:
            event["requestContext"] = {"authorizer": {"claims": {"sub": cognito}}}
        if iam is not None:
            event["requestContext"] = {"identity": {"userArn": iam}}

        if path_params is not None:
            event["pathParameters"] = path_params

        if query_params is not None:
            event["queryStringParameters"] = query_params

        return event

    return _apigateway_event


def context():
    """
    Return a fake Lambda context object

    To use this within a test module, do:

        from fixtures import context
        context = pytest.fixture(context)
    """

    class FakeContext:
        function_name = "FUNCTION_NAME"
        memory_limit_in_mb = 1024
        invoked_function_arn = "INVOKED_FUNCTION_ARN"
        aws_request_id = "AWS_REQUEST_ID"
        log_group_name = "LOG_GROUP_NAME"
        log_stream_name = "LOG_STREAM_NAME"

        def get_remaining_time_in_millis(self):
            # 5 minutes
            return 300000

    return FakeContext()


def lambda_module(request):
    """
    Main module of the Lambda function

    This also load environment variables and the path to the Lambda function
    prior to loading the module itself.

    To use this within a test module, do:

        from fixtures import lambda_module
        lambda_module = pytest.fixture(scope="module", params=[{
            "function_dir": "function_dir",
            "module_name": "main",
            "environ": {
                "ENVIRONMENT": "test",
                "EVENT_BUS_NAME": "EVENT_BUS_NAME",
                "POWERTOOLS_TRACE_DISABLED": "true"
            }
        }])(lambda_module)
    """

    # Inject environment variables
    backup_environ = {}
    for key, value in request.param.get("environ", {}).items():
        if key in os.environ:
            backup_environ[key] = os.environ[key]
        os.environ[key] = value

    # Add path for Lambda function
    sys.path.insert(0, os.path.join(os.environ["ECOM_BUILD_DIR"], "src", request.param["function_dir"]))

    # Save the list of previously loaded modules
    prev_modules = list(sys.modules.keys())

    # Return the function module
    module = importlib.import_module(request.param["module_name"])
    yield module

    # Delete newly loaded modules
    new_keys = list(sys.modules.keys())
    for key in new_keys:
        if key not in prev_modules:
            del sys.modules[key]

    # Delete function module
    del module

    # Remove the Lambda function from path
    sys.path.pop(0)

    # Restore environment variables
    for key in request.param.get("environ", {}).keys():
        if key in backup_environ:
            os.environ[key] = backup_environ[key]
        else:
            del os.environ[key]


@pytest.fixture(scope="module")
def get_order(get_product):
    """
    Returns a random order generator function based on
    shared/resources/schemas.yaml

    Usage:

        from fixtures import get_order
        order = get_order()
    """

    def _get_order(
            order_id: Optional[str] = None,
            user_id: Optional[str] = None,
            products: Optional[List[dict]] = None,
            address: Optional[dict] = None
        ):
        now = datetime.datetime.now()

        order = {
            "orderId": order_id or str(uuid.uuid4()),
            "userId": user_id or str(uuid.uuid4()),
            "createdDate": now.isoformat(),
            "modifiedDate": now.isoformat(),
            "status": "NEW",
            "products": products or [
                get_product() for _ in range(random.randrange(2, 8))
            ],
            "address": address or {
                "name": "John Doe",
                "companyName": "Test Co",
                "streetAddress": "{} Test St".format(random.randint(10, 100)),
                "postCode": str((random.randrange(10**4, 10**5))),
                "city": "Test City",
                "state": "Test State",
                "country": "".join(random.choices(string.ascii_uppercase, k=2)),
                "phoneNumber": "+{}".format(random.randrange(10**9, 10**10))
            },
            "paymentToken": str(uuid.uuid4()),
            "deliveryPrice": random.randint(0, 1000)
        }

        # Insert products quantities and calculate total cost of the order
        total = order["deliveryPrice"]
        for product in order["products"]:
            product["quantity"] = random.randrange(1, 10)
            total += product["quantity"] * product["price"]
        order["total"] = total

        return order

    return _get_order


@pytest.fixture(scope="module")
def get_product():
    """
    Returns a random product generator function based on
    shared/resources/schemas.yaml

    Usage:

       from fixtures import get_product
       product = get_product()
    """

    PRODUCT_COLORS = [
        "Red", "Blue", "Green", "Grey", "Pink", "Black", "White"
    ]
    PRODUCT_TYPE = [
        "Shoes", "Socks", "Pants", "Shirt", "Hat", "Gloves", "Vest", "T-Shirt",
        "Sweatshirt", "Skirt", "Dress", "Tie", "Swimsuit"
    ]

    def _get_product():
        color = random.choice(PRODUCT_COLORS)
        category = random.choice(PRODUCT_TYPE)
        now = datetime.datetime.now()

        return {
            "productId": str(uuid.uuid4()),
            "name": "{} {}".format(color, category),
            "createdDate": now.isoformat(),
            "modifiedDate": now.isoformat(),
            "category": category,
            "tags": [color, category],
            "pictures": [
                "https://example.local/{}.jpg".format(random.randrange(0, 1000))
                for _ in range(random.randrange(5, 10))
            ],
            "package": {
                "weight": random.randrange(0, 1000),
                "height": random.randrange(0, 1000),
                "length": random.randrange(0, 1000),
                "width": random.randrange(0, 1000)
            },
            "price": random.randrange(0, 1000)
        }

    return _get_product