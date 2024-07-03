import datetime
import os
import random
import string
import time
from typing import List
import uuid
import boto3
from locust import HttpUser, between, events, task


MIN_PRODUCTS = 2
MAX_PRODUCTS = 8
SLEEP_TIME = 8


CONFIG = {}
ENVIRONMENT = os.environ["ECOM_ENVIRONMENT"]
ssm = boto3.client("ssm")


def get_products(n=50) -> List[dict]:
    """
    Generate random products and store them in the Products table
    """

    def _get_product() -> dict:
        color = random.choice([
            "Red", "Blue", "Green", "Grey", "Pink", "Black", "White"
        ])
        category = random.choice([
            "Shoes", "Socks", "Pants", "Shirt", "Hat", "Gloves", "Vest", "T-Shirt",
            "Sweatshirt", "Skirt", "Dress", "Tie", "Swimsuit"
        ])
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

    products = [_get_product() for _ in range(n)]

    table_name = ssm.get_parameter(Name=f"/ecommerce/{ENVIRONMENT}/products/table/name")["Parameter"]["Value"]
    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member

    with table.batch_writer() as batch:
        for product in products:
            batch.put_item(Item=product)

    return products


def delete_products(products: List[dict]):
    """
    Delete products
    """

    table_name = ssm.get_parameter(Name=f"/ecommerce/{ENVIRONMENT}/products/table/name")["Parameter"]["Value"]
    table = boto3.resource("dynamodb").Table(table_name) # pylint: disable=no-member

    with table.batch_writer() as batch:
        for product in products:
            batch.delete_item(Key={"productId": product["productId"]})


def get_addresses(n=50) -> List[dict]:
    """
    Generate random addresses
    """

    def _get_address() -> dict:
        return {
            "name": "John Doe",
            "companyName": "Test Co",
            "streetAddress": "{} Test St".format(random.randint(10, 100)),
            "postCode": str((random.randrange(10**4, 10**5))),
            "city": "Test City",
            "state": "Test State",
            "country": "".join(random.choices(string.ascii_uppercase, k=2)),
            "phoneNumber": "+{}".format(random.randrange(10**9, 10**10))
        }

    return [_get_address() for _ in range(n)]


def get_user() -> dict:
    """
    Create a Cognito user
    """

    user_pool_id = ssm.get_parameter(Name=f"/ecommerce/{ENVIRONMENT}/users/user-pool/id")["Parameter"]["Value"]
    cognito = boto3.client("cognito-idp")

    # Create a Cognito User Pool Client
    response = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName="ecommerce-{}-frontend-api-perf".format(ENVIRONMENT),
        GenerateSecret=False,
        ExplicitAuthFlows=["ADMIN_NO_SRP_AUTH"]
    )

    client_id = response["UserPoolClient"]["ClientId"]

    # Create user with admin permissions
    email = "".join(random.choices(string.ascii_lowercase, k=20))+"@example.local"
    password = "".join(
        random.choices(string.ascii_uppercase, k=10) +
        random.choices(string.ascii_lowercase, k=10) +
        random.choices(string.digits, k=5) +
        random.choices(string.punctuation, k=3)
    )

    response = cognito.admin_create_user(
        UserPoolId=user_pool_id,
        Username=email,
        UserAttributes=[{
            "Name": "email",
            "Value": email
        }],
        MessageAction="SUPPRESS"
    )
    user_id = response["User"]["Username"]
    cognito.admin_set_user_password(
        UserPoolId=user_pool_id,
        Username=user_id,
        Password=password,
        Permanent=True
    )
    cognito.admin_add_user_to_group(
        UserPoolId=user_pool_id,
        Username=user_id,
        GroupName="admin"
    )

    # Create a JWT token
    response = cognito.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={
            "USERNAME": email,
            "PASSWORD": password
        }
    )
    jwt_token = response["AuthenticationResult"]["IdToken"]

    return {
        "client_id": client_id,
        "user_id": user_id,
        "jwt_token": jwt_token
    }

def delete_user(user_info: dict):
    """
    Delete the cognito user
    """

    user_pool_id = ssm.get_parameter(Name=f"/ecommerce/{ENVIRONMENT}/users/user-pool/id")["Parameter"]["Value"]
    cognito = boto3.client("cognito-idp")

    # Delete the user
    cognito.admin_delete_user(
        UserPoolId=user_pool_id,
        Username=user_info["user_id"]
    )

    # Delete the client
    cognito.delete_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=user_info["client_id"]
    )


def get_frontend_api_url():
    return ssm.get_parameter(Name=f"/ecommerce/{ENVIRONMENT}/frontend-api/api/url")["Parameter"]["Value"]


def get_payment_3p_api_url():
    return ssm.get_parameter(Name=f"/ecommerce/{ENVIRONMENT}/payment-3p/api/url")["Parameter"]["Value"]


@events.test_start.add_listener
def on_test_start(**kwargs) -> dict:
    CONFIG["payment_api"] = get_payment_3p_api_url()

    # Generate 50 sample products
    CONFIG["products"] = get_products(50)

    # Generate 50 sample addresses
    CONFIG["addresses"] = get_addresses(50)

    # Create a Cognito user
    CONFIG["user"] = get_user()


@events.test_stop.add_listener
def on_test_stop(**kwargs):
    delete_products(CONFIG["products"])
    delete_user(CONFIG["user"])


class HappyPathUser(HttpUser):
    """
    Simulate a happy path workflow
    """

    host = get_frontend_api_url()

    wait_time = between(2, 4)

    @task
    def happy_path(self):
        order_request = self._get_order_request()

        # Create the order
        order_id = self._create_order(order_request)
        time.sleep(SLEEP_TIME)

        # Process the packaging request
        self._process_packaging(order_id)
        time.sleep(SLEEP_TIME)

        # Process delivery
        self._process_delivery(order_id)
        time.sleep(SLEEP_TIME)


    def _get_order_request(self) -> dict:
        """
        Generate an order request
        """
        # Create an order request
        order_request = {
            "products": random.sample(
                CONFIG["products"], random.randrange(MIN_PRODUCTS, MAX_PRODUCTS)
            ),
            "address": random.choice(CONFIG["addresses"])
        }

        # Get the delivery price
        query = """
        query($input: DeliveryPricingInput!) {
          getDeliveryPricing(input: $input) {
            pricing
          }
        }
        """
        variables = {
            "input": {
                "products": order_request["products"],
                "address": order_request["address"]
            }
        }

        res = self.client.post(
            "/",
            headers={"Authorization": CONFIG["user"]["jwt_token"]},
            json={
                "query": query,
                "variables": variables
            }
        )
        body = res.json()
        order_request["deliveryPrice"] = body["data"]["getDeliveryPricing"]["pricing"]

        # Get a payment token for the order
        total = order_request["deliveryPrice"] + sum([p["price"]*p.get("quantity", 1) for p in order_request["products"]])
        res = self.client.post(CONFIG["payment_api"]+"/preauth", json={
            "cardNumber": "1234567890123456",
            "amount": total
        })
        body = res.json()
        order_request["paymentToken"] =  body["paymentToken"]

        return order_request


    def _create_order(self, order_request) -> str:
        """
        Create an order and return the order ID
        """

        query = """
        mutation ($order: CreateOrderRequest!) {
            createOrder(order: $order) {
                success
                message
                errors
                order {
                    orderId
                }
            }
        }
        """
        variables = {
            "order": order_request
        }

        res = self.client.post(
            "/",
            headers={"Authorization": CONFIG["user"]["jwt_token"]},
            json={
                "query": query,
                "variables": variables
            }
        )
        body = res.json()

        return body["data"]["createOrder"]["order"]["orderId"]


    def _process_packaging(self, order_id: str):
        """
        Process packaging for an order
        """

        # Retrieve the packaging request
        query = """
        query ($input: PackagingInput!) {
            getPackagingRequest(input: $input) {
                orderId
                status
                products {
                    productId
                    quantity
                }
            }
        }
        """
        variables = {
            "input": {
                "orderId": order_id
            }
        }
        res = self.client.post(
            "/",
            headers={"Authorization": CONFIG["user"]["jwt_token"]},
            json={
                "query": query,
                "variables": variables
            }
        )
        body = res.json()

        # Start working on the packaging request
        query = """
        mutation ($input: PackagingInput!) {
            startPackaging(input: $input) {
                success
            }
        }
        """
        variables = {
            "input": {
                "orderId": order_id
            }
        }
        res = self.client.post(
            "/",
            headers={"Authorization": CONFIG["user"]["jwt_token"]},
            json={
                "query": query,
                "variables": variables
            }
        )
        body = res.json()
        assert body["data"]["startPackaging"]["success"] == True

        # Complete the packaging request
        query = """
        mutation ($input: PackagingInput!) {
            completePackaging(input: $input) {
                success
            }
        }
        """
        variables = {
            "input": {
                "orderId": order_id
            }
        }
        res = self.client.post(
            "/",
            headers={"Authorization": CONFIG["user"]["jwt_token"]},
            json={
                "query": query,
                "variables": variables
            }
        )
        body = res.json()
        assert body["data"]["completePackaging"]["success"] == True


    def _process_delivery(self, order_id: str):
        """
        Process delivery for an order
        """

        # Retrieve the delivery request
        query = """
        query($input: DeliveryInput!) {
            getDelivery(input: $input) {
                orderId
                address {
                    name
                    companyName
                    streetAddress
                    postCode
                    city
                    state
                    country
                    phoneNumber
                }
            }
        }
        """
        variables = {
            "input": {
                "orderId": order_id
            }
        }
        res = self.client.post(
            "/",
            headers={"Authorization": CONFIG["user"]["jwt_token"]},
            json={
                "query": query,
                "variables": variables
            }
        )
        body = res.json()
        assert body["data"]["getDelivery"]["orderId"] == order_id

        # Start delivery
        query = """
        mutation ($input: DeliveryInput!) {
            startDelivery(input: $input) {
                success
            }
        }
        """
        variables = {
            "input": {
                "orderId": order_id
            }
        }
        res = self.client.post(
            "/",
            headers={"Authorization": CONFIG["user"]["jwt_token"]},
            json={
                "query": query,
                "variables": variables
            }
        )
        body = res.json()
        assert body["data"]["startDelivery"]["success"] == True

        # Complete delivery
        query = """
        mutation ($input: DeliveryInput!) {
            completeDelivery(input: $input) {
                success
            }
        }
        """
        variables = {
            "input": {
                "orderId": order_id
            }
        }
        res = self.client.post(
            "/",
            headers={"Authorization": CONFIG["user"]["jwt_token"]},
            json={
                "query": query,
                "variables": variables
            }
        )
        body = res.json()
        assert body["data"]["completeDelivery"]["success"] == True