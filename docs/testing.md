Testing strategies
==================

This projects use three different layers of tests to validate that the different services are behaving as expected. __Unit tests__ validate that the code within AWS Lambda functions is working properly, __integration tests__ validate that a specific microservice honors its contracts, and __end-to-end tests__ simulate the entire flow to see that core functionalities from the user perspectives are working as expected.

<p align="center">
  <img src="images/testing_workflow.png" alt="Developer workflow"/>
</p>

These multiple layers of tests also helps with ensuring that individual tests are working as expected. As test code is code, it is also prone to bugs and errors.

## End-to-end tests

<p align="center">
  <img src="images/flow.png" alt="User flow"/>
</p>

The __end-to-end tests__ mimick the steps that customers and internal staff would go through to fulfill an order. They only use the external APIs to both act and validate that their actions resulted in the right outcome. For example, a customer creating a valid order should result in a packaging request in the _warehouse_ service's API to retrieve incoming packaging requests. You can find those tests [in the shared folder](../shared/tests/e2e/).

As they look at the entire application as a black box, they do not necessarily help with finding the root cause of an issue. In the previous case, the failure could reside in the _orders_ or in the _warehouse_ service.

As part of the deployment process, they work well to sanity-check that the entire system is behaving as expected, but multiple parallel deployment from different services could make one service pipeline fail because of an issue in another service. For that reason, they are run _after_ the integration tests.

## Integration tests

<p align="center">
  <img src="../delivery/images/delivery.png" alt="Delivery architecture diagram" />
</p>

The purpose of the __integration tests__ is to test that the promises of the service are being met. For example, if a service needs to react to a specific event, these tests will send that event onto the event bus and compare the results with the desired outcome. These tests are bounded to a given service, and thus do not serve the purpose of testing integration between services (which is done by end-to-end tests).

For example, when the _warehouse_ service creates a package, it emits an event to EventBridge. The _delivery_ service should pick that event up and create an item in DynamoDB. Therefore, an integration test will create that event and look if the item was properly created in DynamoDB.

This type of test has the benefit of validating that the resources are configured properly, such as making sure that the Lambda function is triggered by events from EventBridge, that it has the right permissions to access the DynamoDB table, etc. in an actual AWS environment.

However, one downside of this approach is that, because the _delivery_ service fakes events from the _warehouse_ service, it has to rely that the _warehouse_ service's documentation is correct. If the event when a package is created is slightly different and doesn't match the rule, the integration tests could pass, but the service would never receive those events. However, the end-to-end tests help catch these types of issues.

On the integration with other services, there are two possible strategies: either services provide mocks (APIs and way to generate events), or services are called during the integration tests of a given service. This project uses the latter option for simplicity and to reduce the overhead of keeping the mocks in sync.

This means that integration tests for one service could be tangled to another service's architecture. For example, when testing the create order path of the _orders_ service, it will make calls to the _products_ service to validate that the products in the order request exist. Therefore, the tests need to inject data into the _products_ database. If the way to inject those products changes, the test will fail despite the fact that the functionality itself might be working properly. This thus requires adapting tests due to external changes that do not affect the functionalities in scope of the test.

## Unit tests

Many functional aspects of a service are already tested by the end-to-end and integration tests. __Unit tests__ provide a few additional benefits and are complementary to the other types of test.

First, they are much quicker to run as they do not need to deploy or update resources on AWS. This means that unit tests can potentially explore more scenarios in a given timeframe than the other types of test.

Given the fact that they test code locally, code coverage tools can be used to ensure that they cover all branches and functions for all Lambda functions within a service. For this reason, we enforce a test coverage of [at least 90%](../shared/tests/unit/coveragerc).

Finally, as a service should have multiple layers of security controls to prevent against misconfiguration, unit tests could test code branches that are not used in normal operation. For example, if a function behind an API Gateway should only be called with IAM credentials, the API Gateway will normally reject requests without a proper authorization header. However, as a best practice, the Lambda function code should check if IAM credentials are present. This section of code will never be used in normal operations, but still needs to be present to protect against configuration mishaps.

## Lint

To enforce a certain quality standard and set of stylistic rules across the entire project, lint tools analyze the code for CloudFormation templates, OpenAPI documents and Lambda function source code.

For CloudFormation templates, there are [additional rules](../shared/lint/rules/) specific to this project, such as enforcing that all Lambda function have a corresponding CloudWatch Logs log group, or that functions called asynchronously have a [destination](https://aws.amazon.com/blogs/compute/introducing-aws-lambda-destinations/) in case of failures to process the messages.

## Running tests

When using the _ci_ or _all_ command on a service (e.g. `make ci-$SERVICE` or `make all-$SERVICE`), this will automatically run the linting, unit tests for _ci_ and linting, unit and integration tests for _all_. However, if you want to run the tests manually, you can use the following commands:

* `make lint-$SERVICE`
* `make tests-unit-$SERVICE`
* `make tests-integ-$SERVICE`
* `make tests-e2e`

__Remark__: As end-to-end tests look at the flow across services, you cannot run these for a specific service, only for the entire platform. This means that all services should be deployed for those tests to work properly.

### As part of the deployment pipeline

When using the [deployment pipeline](../pipeline/), the first stage performs lint and unit tests before creating artifacts per service, which trigger a per-service pipeline. The pipeline first deploys the service into a _tests_ environment, against which integration tests are run, then afterwards into a _staging_ environment where end-to-end are run. If the end-to-end tests pass successfully, the service is then deployed into the production environment.

As nothing forces developers to test before committing, putting all tests as part of the pipeline ensure that the tests are run at least once.

## Writing tests

When using one of [the default Makefiles](../shared/makefiles/), unit tests should be in the `$SERVICE/tests/unit/` folder, and integration tests in the `$SERVICE/tests/integ/` folder. Files will automatically get picked up by the testing commands. As most of the project is written using Python 3, this section covers tests for this language. If you want to see how to perform testing with Typescript and CDK, see the [payment-3p](../payment-3p/) service.

Both unit and integration tests for Python 3 templates are run using [pytest](https://docs.pytest.org/en/latest/).

### Unit tests

When writing unit tests, you can import helpers and fixtures from [files in the shared folder](../shared/tests/unit/). To import the Lambda function module, you can use the `lambda_module` fixture, which takes care of setting the path to find modules in your function folder and setting environment variables. It also resets everything at the end of the test file.

```python
import pytest
from fixtures import lambda_module


lambda_module = pytest.fixture(
    # This fixture will only be initialized once for the entire module.
    scope="module",
    params=[{
        # Folder name of your function code.
        # If your function is stored at "src/my_function/" in your service
        # folder, the value should be "my_function".
        # Under the hood, this will use the folder at "build/src/my_function".
        "function_dir": "my_function",
        # The module that you want to load from your function code. Usually,
        # this is the one containing the Lambda handler.
        "module_name": "main",
        # Use this to inject environment variables as needed.
        "environ": {
            "ENVIRONMENT": "tests",
            "EVENT_BUS_NAME": "EVENT_BUS_NAME",
            "POWERTOOLS_TRACE_DISABLED": "true"
        }
    }]
# This wraps the lambda_module function to transform it into a fixture for this
# file.
)(lambda_module)
```

You can then use your Lambda function module as such:

```python
def test_my_add_function(lambda_module):
    """
    Test my_add_function()
    """

    arg_a = 3
    arg_b = 4

    # lambda_module correspond to the module_name of your Lambda function.
    retval = lambda_module.my_add_function(arg_a, arg_b)

    assert retval == arg_a + arg_b
```

The [fixtures.py file](../shared/tests/unit/fixtures.py) also provide other useful fixtures such as a context for Lambda handlers, sample API Gateway event, fixture to generate orders or products, etc.

#### Mocking the AWS SDK

As Lambda functions often interact with AWS services, it is important to stub or mock API calls to verify that they are making the right calls. To do so, you can use the [Stubber class](https://botocore.amazonaws.com/v1/documentation/api/latest/reference/stubber.html) provided by botocore.

As a safety measure, the _tests-unit_ command sets up AWS credentials environment variables with fake values to prevent making calls with valid credentials in case you forget to stub calls.

Here is how you can stub API calls for a DynamoDB get_item call:

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

### Integration tests

As integration tests run against resources on AWS, it's important to be able to retrieve those values. The AWS Systems Manager Parameter Store is already used [for service discovery](./service_discovery.md), but it can also be used to expose internal parameters for testing and debugging. For example, a service could expose a parameter named `/ecommerce/{Environment}/{ServiceName}/table/name` for its DynamoDB table name.

In the shared folder, the [helpers file](../shared/tests/integ/helpers.py) contains a `get_parameter` function to retrieve the value of such parameters. For example, if you want to retrieve the Event Bus name from the platform service:

```python
import pytest
from helpers import get_parameter


# Exposes the parameter value as a fixture
@pytest.fixture
def event_bus_name():
    """
    EventBridge event bus name from the Platform service
    """

    # Retrieve the parameter value
    return get_parameter("/ecommerce/{Environment}/platform/event-bus/name")


# Uses the fixture in this function
def test_my_test(event_bus_name):
    """
    Test something
    """

    # Do something with the event bus name
```

If a service sends messages onto the event bus, you can use the [listener stack](../shared/templates/listener.yaml) and its corresponding [listener fixture](../shared/tests/integ/fixtures.py). The stack can be used as a `AWS::CloudFormation::Stack` resource within the service stack and will contain an SQS queue with all messages matching the service name. The listener fixture will retrieve all messages on the queue for a specified time interval.

To use the listener stack in the service's CloudFormation template:

```yaml
# As the listener stack is only useful for the testing environments, we use a
# condition to limit deployment of the listener stack to non-production
# environments only.
Conditions:
  IsNotProd: !Not [!Equals [!Ref Environment, prod]]


Resources:
  Listener:
    Type: AWS::CloudFormation::Stack
    # This will deploy this resource only if IsNotProd evaluates to true.
    Condition: IsNotProd
    Properties:
      # Relative path to the listener stack. The path is relative to the build
      # folder ($SERVICE/build/).
      TemplateURL: ../../shared/templates/listener.yaml
      Parameters:
        Environment: !Ref Environment
        EventBusName: !Ref EventBusName
        ServiceName: "my-service"
```

Then in an integration test:

```python
from fixtures import listener


def test_something(listener):
    """
    Test a service that emits an event
    """

    # Do something that triggers an event
    requests.post(endpoint_url, data={"key": "value"})

    # Listen to events
    # By default, this listens for 15 seconds, but you can override that value.
    messages = listener("your-service")

    # Parse messages
    found = False
    for message in messages:
        body = json.loads(message["Body"])
        if body["key"] == "value":
            found = True
            # You might want to do additional assertions here

    assert found == True
```