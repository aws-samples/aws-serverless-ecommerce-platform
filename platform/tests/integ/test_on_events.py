import asyncio
import datetime
import hashlib
import hmac
import json
import time
import urllib
import uuid
import boto3
import pytest
import websockets # pylint: disable=import-error

from fixtures import listener #pylint: disable=import-error
from helpers import get_parameter # pylint: disable=no-name-in-module


@pytest.fixture(scope="module")
def listener_api_url():
    return get_parameter("/ecommerce/{Environment}/platform/listener-api/url")


@pytest.fixture(scope="module")
def event_bus_name():
    return get_parameter("/ecommerce/{Environment}/platform/event-bus/name")


def test_listener(listener, event_bus_name):
    service_name = "ecommerce.test"
    resource = str(uuid.uuid4())
    event_type = "TestEvent"

    events = boto3.client("events")

    listener(service_name, lambda:
        events.put_events(Entries=[{
            "Time": datetime.datetime.utcnow(),
            "Source": service_name,
            "Resources": [resource],
            "DetailType": event_type,
            "Detail": "{}",
            "EventBusName": event_bus_name
        }]),
        lambda x: (
            x["source"] == service_name and
            x["resources"][0] == resource and
            x["detail-type"] == event_type
        )
    )
