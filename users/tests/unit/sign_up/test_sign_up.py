import copy
import datetime
import json
import uuid
import pytest
from botocore import stub
from fixtures import context, lambda_module
from helpers import compare_event


lambda_module = pytest.fixture(scope="module", params=[{
    "function_dir": "sign_up",
    "module_name": "main",
    "environ": {
        "ENVIRONMENT": "test",
        "EVENT_BUS_NAME": "EVENT_BUS_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
context = pytest.fixture(context)


@pytest.fixture
def postconfirm_data():
    input_ = {
        "version": 1,
        "triggerSource": "PostConfirmation_ConfirmSignUp",
        "region": "eu-west-1",
        "userPoolId": "eu-west-1_ABCDEFGHI",
        "userName": str(uuid.uuid4()),
        "callerContext": {
            "awsSdkVersion": "1",
            "clientId": "abcdefg"
        },
        "request": {
            "userAttributes": {
                "email": "john.doe@example.com"
            }
        },
        "response": {}
    }

    output = {
        "Source": "ecommerce.users",
        "Resources": [
            input_["userName"]
        ],
        "DetailType": "UserCreated",
        "Detail": json.dumps({
            "userId": input_["userName"],
            "email": input_["request"]["userAttributes"]["email"]
        })
    }

    return {
        "input": input_,
        "output": output
    }


def test_process_request(lambda_module, postconfirm_data):
    """
    Test process_request()
    """

    retval = lambda_module.process_request(postconfirm_data["input"])

    compare_event(postconfirm_data["output"], retval)


def test_send_event(lambda_module, postconfirm_data):
    """
    Test send_event()
    """

    eventbridge = stub.Stubber(lambda_module.eventbridge)

    event = postconfirm_data["output"]
    response = {}
    expected_params = {"Entries": [event]}

    eventbridge.add_response("put_events", response, expected_params)
    eventbridge.activate()

    lambda_module.send_event(event)

    eventbridge.assert_no_pending_responses()
    eventbridge.deactivate()


def test_handler(lambda_module, context, postconfirm_data):
    """
    Test handler()
    """

    output = copy.deepcopy(postconfirm_data["output"])
    output["Time"] = stub.ANY

    # Prepare stub
    eventbridge = stub.Stubber(lambda_module.eventbridge)
    response = {}
    expected_params = {"Entries": [output]}
    eventbridge.add_response("put_events", response, expected_params)
    eventbridge.activate()

    # Execute function
    lambda_module.handler(postconfirm_data["input"], context)

    # End
    eventbridge.assert_no_pending_responses()
    eventbridge.deactivate()