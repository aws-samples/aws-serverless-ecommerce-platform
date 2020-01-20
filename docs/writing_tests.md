Writing tests
=============

* [Unit tests](#unit-tests)
* [Integration tests](#integration-tests)
* [End-to-end tests](#end-to-end-tests)

## Unit tests

In the context of this project, __unit tests__ refers to tests of pieces of code within the Lambda functions themselves. For example, testing a Python function within the code of a specific Lambda function. These tests can be performed without deploying resources to AWS, but require to build the resources.

To add tests for your service, you must create a `tests/unit` within your service folder and write test cases using [pytest](https://docs.pytest.org/en/latest/) conventions. The `shared/tests/unit` folder is present in `sys.path` and contains fixtures and tools to help with testing code within Lambda functions.

Unit tests should have a test coverage of __at least 90%__. Otherwise, `tools/toolbox $SERVICE tests-unit` will return a failure.

### `lambda_module` fixture

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

## Integration tests

In the context of this project, __integration tests__ refers to tests of components _within the boundaries of a service_ (e.g. products, orders) that span multiple AWS resources and ensures that these resources integrate and behave together as expected. For example, testing that a DynamoDB triggers a Lambda function, and that that Lambda function takes the appropriate action. Compared to [unit tests](#unit-tests), integration tests ensure that the integration between these resources work as expected. These tests require resources to be deployed on AWS.

## End-to-end tests

In the context of this project, __end-to-end tests__ refers to tests of functionalities across _multiple services_. These tests should ideally be written from the perspective of the _end user_ and ensure that high level features work as expected (e.g. a user is able to place an order, check their orders, etc.). These tests require resources to be deployed on AWS.