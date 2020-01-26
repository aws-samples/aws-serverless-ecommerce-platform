Testing
=======

* [Unit tests](#unit-tests)
  * [Writing tests](#writing-tests)
  * [Helper modules](#helper-modules)
  * [Mocking boto3](#mocking-boto3)
  * [Running tests](#running-tests)
* [Integration tests](#integration-tests)
  * [Writing tests](#writing-tests-1)
  * [Listener template](#listener-template)
  * [Helper modules](#helper-modules-1)
  * [SSM Parameters](#ssm-parameters)
  * [Running tests](#running-tests-1)
* [End-to-end tests](#end-to-end-tests)

## Unit tests

In the context of this project, __unit tests__ refers to tests of pieces of code within the Lambda functions themselves. For example, testing a Python function within the code of a specific Lambda function. These tests can be performed without deploying resources to AWS, but require to build the resources.

### Writing tests

To add tests for your service, you must create a `tests/unit` folder within your service folder and write test cases using [pytest](https://docs.pytest.org/en/latest/) conventions. The [shared/tests/unit](../shared/tests/unit) folder is present in `sys.path` and contains fixtures and tools to help with testing code within Lambda functions.

Unit tests should have a test coverage of __at least 90%__. Otherwise, `tools/toolbox $SERVICE tests-unit` will return a failure.

### Helper modules

To help loading your Lambda function in a safe manner, you can use the convenience fixtures defined in [shared/tests/unit/](../shared/tests/unit/). This folder is loaded in the python path.

To load your Lambda function as a pytest fixture, add the following piece of code in your test module:

```python
import pytest
from fixtures import lambda_module

lambda_module = pytest.fixture(scope="module", params=[{
    # Folder name of your function code.
    # If your function is stored at "src/my_function/" in your service folder,
    # the value should be "my_function".
    "function_dir": "function_dir",
    # The module that you want to load from your function code. Usually, this
    # is the one containing the Lambda handler.
    "module_name": "main",
    # Use this to inject environment variables as needed.
    "environ": {
        "ENVIRONMENT": "tests",
        "EVENT_BUS_NAME": "EVENT_BUS_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}]
)(lambda_module)
```

When performing unit tests against a Lambda handler and if you are using a tracing and logging tool such as [aws-lambda-powertools](https://github.com/awslabs/aws-lambda-powertools/tree/develop/python), you might need to use a fake context. For this, you can load a context fixture like such:

```python
import pytest
from fixtures import context

context = pytest.fixture(context)
```

You can then use these fixtures in your tests as such:

```python
test_handler(lambda_module, context):
    """
    Test handler()
    """

    # Prepare your test
    event = {
        # ...
    }

    response = lambda_module.handler(event, context)

    # Perform assertions against the handler's return value
    # For example, for an API Gateway Proxy integration:
    assert response["statusCode"] == 200
    # ...
```

### Mocking boto3

First of all, as a safety measure, the tests-unit commands from [toolbox CLI](toolbox.md) sets up AWS credentials environment variables with fake values that should fail if you forget to mock boto3.

To mock boto3 calls, you can use the [Stubber class provided by botocore](https://botocore.amazonaws.com/v1/documentation/api/latest/reference/stubber.html).

For example, to mock a DynamoDB get_item call:

```python
from boto3.dynamodb.types import TypeSerializer 

def test_dynamodb(lambda_module, item):
    """
    Tests a function that calls DynamoDB
    """

    # Replace dynamodb/table by your client/resource name.
    # If you use a resource instead of a client, use this instead:
    # table = stub.Stubber(lambda_module.table.meta.client)
    dynamodb = stub.Stubber(lambda_module.dynamodb)

    # Create the expected response
    response = {
        "Item": {
            key: TypeSerializer().serialize(value) 
            for key, value in item.items()
        }
    }

    # Expected parameters in the request
    expected_params = {
        "TableName": lambda_module.TABLE_NAME,
        "Key": {"pk": item["pk"]}
    }

    # Add the response
    dynamodb.add_response("get_item", response, expected_params)

    # Activate the stubber
    dynamodb.activate()

    # Run your command
    retval = lambda_module.my_function(item["pk"])

    # Assert that the stub was called
    dynamodb.assert_no_pending_responses()

    # Deactivate the stub
    dynamodb.deactivate()

    # Check the response
    assert item["pk"] == retval["pk"]
    # ...
```

### Running tests

To run unit tests against a specific service, you can run the following command:

```bash
tools/toolbox $SERVICE tests-unit

# Clean and build resources before running the tests
tools/toolbox $SERVICE clean build tests-unit
```

## Integration tests

In the context of this project, __integration tests__ refers to tests of components _within the boundaries of a service_ (e.g. products, orders) that span multiple AWS resources and ensures that these resources integrate and behave together as expected. For example, testing that a DynamoDB triggers a Lambda function, and that that Lambda function takes the appropriate action. Compared to [unit tests](#unit-tests), integration tests ensure that the integration between these resources work as expected. These tests require resources to be deployed on AWS.

### Writing tests

To add integration tests for your service, you must create a `tests/integ` folder within the service folder and write test cases using [pytest](https://docs.pytest.org/en/latest/) conventions. The [shared/tests/integ](../shared/tests/integ) folder is present in `sys.path` and contains fixtures and tools to help with writing integration tests.

### Listener template

If your integration tests require to validate that message are sent to the [EventBridge event bus](https://docs.aws.amazon.com/eventbridge/latest/userguide/what-is-amazon-eventbridge.html) defined by the platform stack, you can use the listener stack defined at [shared/templates/listener.yaml](../shared/templates/listener.yaml). This stack contains a rule that will capture all messages matching the source of your service and store them to an SQS queue.

To include the listener stack, you can add this in your CloudFormation template:

```yaml
Conditions:
  # In the condition section, check if the stack is in production
  IsNotProd: !Not [!Equals [!Ref Environment, prod]]

Resources:
  # In the resource section, add the following resource:
  Listener:
    Type: AWS::CloudFormation::Stack
    # The condition ensures that this will not get deployed in production
    Condition: IsNotProd
    Properties:
      TemplateURL: ../../shared/templates/listener.yaml
      Parameters:
        # Replace this with your service name
        ServiceName: "products"
```

This will create an SSM parameter called `/ecommerce/{service}/listener/url` that you can use in the test modules.

When using the listener template, as reading messages from the SQS queue will empty that queue, you should not run multiple tests in parallel. It is also recommended to perform all tests that listen to events in the same test module, and listen for all messages for a fixed period of time for every test case.

### Helper modules

To help with common testing scenarios, you can use the convenience fixtures defined in [shared/tests/integ/](../shared/tests/integ/). This folder is loaded in the python path.

For example, if you are using a listener stack to listen to incoming EventBridge events, you can use a listener fixtures that will automatically listen on the SQS queue defined in that stack for a fixed period of time. You can use this fixture as such:

```python
import pytest
from fixtures import listener

listener = pytest.fixture(scope="module", params=[{
    # Replace 'your-service' with your service name
    "service": "your-service"
}])(listener)
```

Then, to listen to messages within a test case:

```python
import requests

def test_listen_to_event(listener, endpoint_url):
    """
    Listens to an event emitted to EventBridge
    """

    # Do something that triggers an event
    requests.post(endpoint_url, data={"key": "value"})

    # Listen to events
    messages = listener()

    # Parse messages
    found = False
    for message in messages:
        body = json.loads(message["Body"])
        if body["key"] == "value":
            found = True
            # You might want to do additional assertions here

    assert found == True
```

### SSM Parameters

As each service uses SSM parameters to export values, you can leverage those to retrieve values within your integration tests. To know which environment to grab, you can use the `ECOM_ENVIRONMENT` environment variable.

For example, if you want to retrieve a DynamoDB table name and API Gateway URL:

```python
import os
import boto3


ssm = boto3.client("ssm")
ECOM_ENVIRONMENT = os.environ["ECOM_ENVIRONMENT"]


@pytest.fixture
def table_name(scope="module"):
    return ssm.get_parameter(
        # Replace 'your-service' by your service name
        Name="/ecommerce/{}/your-service/table/name".format(ECOM_ENVIRONMENT)
    )["Parameter"]["Value"]


@pytest.fixture
def endpoint_url(scope="module"):
    return ssm.get_parameter(
        # Replace 'your-service' by your service name
        Name="/ecommerce/{}/your-service/api/url".format(ECOM_ENVIRONMENT)
    )["Parameter"]["Value"]
```

### Running tests

To run integration tests against a specific service, you can run the following command:

```bash
tools/toolbox $SERVICE tests-integ

# Clean, build and deploy resources before running the tests
tools/toolbox $SERVICE clean build package deploy tests-integ
```

## End-to-end tests

In the context of this project, __end-to-end tests__ refers to tests of functionalities across _multiple services_. These tests should ideally be written from the perspective of the _end user_ and ensure that high level features work as expected (e.g. a user is able to place an order, check their orders, etc.). These tests require resources to be deployed on AWS.

_End-to-end tests are not implemented yet. Please see the [issue related to that feature](https://github.com/aws-samples/aws-serverless-ecommerce-platform/issues/3)_.