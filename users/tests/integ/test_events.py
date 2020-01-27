import uuid
import json
import os
import random
import string
import boto3
import pytest
from fixtures import listener


ssm = boto3.client("ssm")


COGNITO_USER_POOL = ssm.get_parameter(
    Name="/ecommerce/{}/users/user-pool/id".format(os.environ["ECOM_ENVIRONMENT"])
)["Parameter"]["Value"]


cognito = boto3.client("cognito-idp")


@pytest.fixture
def user_id():
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
    user_id = response["User"]["Username"]

    # # Set a user password
    # cognito.admin_set_user_password(
    #     UserPoolId=COGNITO_USER_POOL,
    #     Username=user_id,
    #     Password=password,
    #     Permanent=True
    # )
    
    # cognito.admin_confirm_sign_up(
    #     UserPoolId=COGNITO_USER_POOL,
    #     Username=user_id
    # )

    # Return the user ID
    yield user_id

    # Delete the user
    cognito.admin_delete_user(
        UserPoolId=COGNITO_USER_POOL,
        Username=user_id
    )


def test_sign_up(listener, user_id):
    """
    Test that the SignUp function reacts to new users in Cognito User Pools and
    sends an event to EventBridge
    """

    # Listen for messages on EventBridge through a listener SQS queue
    messages = listener("users")

    # Parse messages
    found = False
    for message in messages:
        print("MESSAGE RECEIVED:", message)
        body = json.loads(message["Body"])
        if user_id in body["resources"]:
            found = True
            assert body["detail-type"] == "UserCreated"

    assert found == True
