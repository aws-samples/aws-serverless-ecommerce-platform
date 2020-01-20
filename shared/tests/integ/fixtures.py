import boto3


sqs = boto3.client("sqs")
ssm = boto3.client("ssm")


def listener(request):
    """
    Listens to messages in the Listener queue for a given service for a fixed
    period of time.
    """

    default_timeout = request.param.get("timeout", 30)
    queue_url = ssm.get_parameter(Name="/ecommerce/{}/listener/url".format(request.param["service"]))

    def get_messages(timeout=default_timeout):
        messages = []
        # Wait for a given time period
        # 20 is the maximum amount of time for a single receive_message() call.
        # If timeout is less than 20, this loop will be skipped.
        for _ in range(timeout//20):
            response = sqs.receive_message(
                QueueUrl=queue_url["Parameter"]["Value"],
                WaitTimeSeconds=20
            )
            messages.extend(response.get("Messages", []))
        # Handle remaining time
        if timeout % 20 != 0:
            response = sqs.receive_message(
                QueueUrl=queue_url["Parameter"]["Value"],
                WaitTimeSeconds=timeout % 20
            )
            messages.extend(response.get("Messages", []))

        return messages

    return get_messages