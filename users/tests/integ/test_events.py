import uuid
import json
import os
import random
import string
import boto3
import pytest
from fixtures import listener # pylint: disable=import-error


ssm = boto3.client("ssm")


COGNITO_USER_POOL = ssm.get_parameter(
    Name="/ecommerce/{}/users/user-pool/id".format(os.environ["ECOM_ENVIRONMENT"])
)["Parameter"]["Value"]


cognito = boto3.client("cognito-idp")


def test_sign_up(listener):
    """
    Test that the SignUp function reacts to new users in Cognito User Pools and
    sends an event to EventBridge
    """

    data = {}

    def gen_func():
        email = "".join(random.choices(string.ascii_lowercase, k=20))+"@example.local"
        password = "".join(
            random.choices(string.ascii_uppercase, k=10) +
            random.choices(string.ascii_lowercase, k=10) +
            random.choices(string.digits, k=5) +
            random.choices(string.punctuation, k=3)
        )

        # Create a new user
        response = cognito.admin_create_user(
            UserPoolId=COGNITO_USER_POOL,
            Username=email,
            UserAttributes=[{
                "Name": "email",
                "Value": email
            }],
            # Do not send an email as this is a fake address
            MessageAction="SUPPRESS"
        )
        data["user_id"] = response["User"]["Username"]

    def test_func(m):
        return data["user_id"] in m["resources"] and m["detail-type"] == "UserCreated"

    # Listen for messages on EventBridge
    listener("ecommerce.users", gen_func, test_func)

    cognito.admin_delete_user(
        UserPoolId=COGNITO_USER_POOL,
        Username=data["user_id"]
    )