import os
import time
from urllib.parse import urlparse
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