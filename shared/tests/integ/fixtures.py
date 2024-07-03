import asyncio
import datetime
import json
import hashlib
import hmac
import os
import random
import string
import time
from typing import Callable, List, Optional
from urllib.parse import urlparse
import uuid
from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
import boto3
import pytest
import websockets # pylint: disable=import-error


sqs = boto3.client("sqs")
ssm = boto3.client("ssm")


@pytest.fixture
def listener():
    """
    Listens to messages through a WebSocket API
    """

    def signed_url_headers(url):
        """
        Generate SigV4 signature headers

        Taken from https://docs.aws.amazon.com/general/latest/gr/sigv4-signed-request-examples.html
        """

        def sign(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

        def get_signature_key(key, dateStamp, regionName, serviceName):
            kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
            kRegion = sign(kDate, regionName)
            kService = sign(kRegion, serviceName)
            kSigning = sign(kService, 'aws4_request')
            return kSigning

        uri = urlparse(url)
        session = boto3.Session()
        credentials = session.get_credentials()

        t = datetime.datetime.utcnow()
        amzdate = t.strftime('%Y%m%dT%H%M%SZ')
        datestamp = t.strftime('%Y%m%d')
        canonical_uri = uri.path
        canonical_headers = f"host:{uri.netloc}\nx-amz-date:{amzdate}\n"
        signed_headers = "host;x-amz-date"
        payload_hash = hashlib.sha256(('').encode('utf-8')).hexdigest()
        canonical_request = f"GET\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        canonical_request_enc = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
        credential_scope = f"{datestamp}/{session.region_name}/execute-api/aws4_request"
        string_to_sign = f"AWS4-HMAC-SHA256\n{amzdate}\n{credential_scope}\n{canonical_request_enc}"
        signing_key = get_signature_key(credentials.secret_key, datestamp, session.region_name, "execute-api")
        signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()
        authorization_header = f"AWS4-HMAC-SHA256 Credential={credentials.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

        return {'x-amz-date':amzdate, 'Authorization':authorization_header}

    def _listener(service_name: str, gen_function: Callable[[None], None], test_function: Optional[Callable[[dict], bool]]=None, wait_time: int=15):
        """
        Listener fixture function
        """

        # Retrieve the listener API URL
        listener_api_url = ssm.get_parameter(
            Name="/ecommerce/{}/platform/listener-api/url".format(os.environ["ECOM_ENVIRONMENT"])
        )["Parameter"]["Value"]

        # Inner async function
        async def _listen() -> List[dict]:
            # Generate SigV4 headers
            headers = signed_url_headers(listener_api_url)
            # Connects to API
            async with websockets.connect(listener_api_url, extra_headers=headers) as websocket:
                # Send to which service we are subscribing
                await websocket.send(
                    json.dumps({"action": "register", "serviceName": service_name})
                )

                # Run the function that will produce messages
                gen_function()

                # Listen to messages through the WebSockets API
                found = False
                messages = []
                # Since asyncio.wait_for timeout parameter takes an integer, we need to
                # calculate the value. For this, we calculate the datetime until we want to
                # wait in the worst case, then calculate the timeout integer value based on
                # that.
                timeout = datetime.datetime.utcnow() + datetime.timedelta(seconds=wait_time)
                while datetime.datetime.utcnow() < timeout:
                    try:
                        message = json.loads(await asyncio.wait_for(
                            websocket.recv(),
                            timeout=(timeout - datetime.datetime.utcnow()).total_seconds()
                        ))
                        print(message)
                        messages.append(message)
                        # Run the user-provided test
                        if test_function is not None and test_function(message):
                            found = True
                            break
                    except asyncio.exceptions.TimeoutError:
                        # Timeout exceeded
                        break

                if test_function is not None:
                    assert found == True

                return messages

        return asyncio.run(_listen())

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