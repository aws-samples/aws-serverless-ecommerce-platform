Testing
=======

* [Unit tests](#unit-tests)
  * [Writing tests](#writing-tests)
    * [`lambda_module` fixture](#lambda_module-fixture)
  * [Running tests](#running-tests)
* [Integration tests](#integration-tests)
  * [Writing tests](#writing-tests-1)
    * [Listener template](#listener-template)
    * [`listener` fixture](#listener-fixture)
  * [Running tests](#running-tests-1)
* [End-to-end tests](#end-to-end-tests)

## Unit tests

In the context of this project, __unit tests__ refers to tests of pieces of code within the Lambda functions themselves. For example, testing a Python function within the code of a specific Lambda function. These tests can be performed without deploying resources to AWS, but require to build the resources.

### Writing tests

To add tests for your service, you must create a `tests/unit` folder within your service folder and write test cases using [pytest](https://docs.pytest.org/en/latest/) conventions. The [shared/tests/unit](../shared/tests/unit) folder is present in `sys.path` and contains fixtures and tools to help with testing code within Lambda functions.

Unit tests should have a test coverage of __at least 90%__. Otherwise, `tools/toolbox $SERVICE tests-unit` will return a failure.

#### `lambda_module` fixture

To load the python module in the Lambda function folder containing the handler, you can leverage the `lambda_module` fixture as such:

```python
import pytest
from fixtures import lambda_module

lambda_module = pytest.fixture(scope="module", params=[{
    # Function directory within 'src'
    "function_dir": "function_dir",
    # Python module containing your Lambda handler
    "module_name": "main",
    # Environment variables
    "environ": {
        "ENVIRONMENT": "test",
        "EVENT_BUS_NAME": "EVENT_BUS_NAME",
        "POWERTOOLS_TRACE_DISABLED": "true"
    }
}])(lambda_module)
```

The fixture takes care of adding the Lambda function path (`function_dir`) in `sys.path`, loading the module, updating environment variables. It also takes care of cleaning up modules and environment variables after the test module.

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

#### Listener template

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

#### `listener` fixture

When using the [Listener template](#listener-template), you can use the listener fixture to automatically listen to the SQS queue for a set period of time and collect all messages.

To add the listener as a fixture, add the following in your test module:

```python
import pytest
from fixtures import listener

listener = pytest.fixture(scope="module", params=[{
    "service": "service_name"}
])(listener)
```

You can then use the listener in your test cases:


```python
def test_sending_events(listener):
    # Make actions that should trigger an event
    # ...
    resource_id = str(uuid.uuid4())
    message_type = "ObjectDeleted"

    messages = listener()

    for message in messages:
        # Parse messages
        body = json.loads(message["Body"])

        assert body["source"] == "ecommerce.{}".format(SERVICE_NAME)
        assert resource_id in body["resources"]
        assert body["detail-type"] == message_type
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

__Remark__: end-to-end tests are not implemented yet. Please see the [issue related to that feature](https://github.com/aws-samples/aws-serverless-ecommerce-platform/issues/3).