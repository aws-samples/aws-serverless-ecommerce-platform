import datetime
import os
import random
import string
import time
from typing import List, Optional
from urllib.parse import urlparse
import uuid
from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
import boto3
import pytest


sqs = boto3.client("sqs")
ssm = boto3.client("ssm")


@pytest.fixture
def listener(request):
    """
    Listens to messages in the Listener queue for a given service for a fixed
    period of time.

    To use in your integration tests:

        from fixtures import listener

    Then to write a test:

        test_with_listener(listener):
            # Trigger an event that would result in messages
            # ...

            messages = listener("your-service")

            # Parse messages
    """

    def _listener(service_name: str, timeout: int=15):
        queue_url = ssm.get_parameter(
            Name="/ecommerce/{}/{}/listener/url".format(
                os.environ["ECOM_ENVIRONMENT"], service_name
            )
        )["Parameter"]["Value"]

        print("TIMEOUT", timeout)
        messages = []
        start_time = time.time()
        while time.time() < start_time + timeout:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=min(20, int(time.time()-start_time+timeout))
            )
            if response.get("Messages", []):
                sqs.delete_message_batch(
                    QueueUrl=queue_url,
                    Entries=[
                        {"Id": m["MessageId"], "ReceiptHandle": m["ReceiptHandle"]}
                        for m in response["Messages"]
                    ]
                )
            messages.extend(response.get("Messages", []))

        return messages
    
    return _listener


@pytest.fixture
def iam_auth():
    """
    Helper function to return auth for IAM
    """

    def _iam_auth(endpoint):
        url = urlparse(endpoint)
        region = boto3.session.Session().region_name

        return BotoAWSRequestsAuth(
            aws_host=url.netloc,
            aws_region=region,
            aws_service="execute-api"
        )

    return _iam_auth


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