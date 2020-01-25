Service structure
=================

* [`metadata.yaml`](#metadatayaml)
* [`template.yaml`](#templateyaml)
  * [Capabilities](#capabilities)
  * [API Gateway](#api-gateway)
  * [SSM Parameters](#ssm-parameters)
  * [Listener stack](#listener-stack)
* [`resources/openapi.yaml`](#resourcesopenapiyaml)
  * [Authorizers](#authorizers)
  * [Lambda integrations](#lambda-integrations)
* [`resources/events.yaml`](#resourceseventsyaml)
* [`src/` folder](#src-folder)
  * [requirements.txt](#requirementstxt)
  * [`ecom` module](#ecom-module)
* [`tests/unit/` folder](#testsunit-folder)
  * [Helper modules](#helper-modules)
  * [Mocking boto3](#mocking-boto3)
* [`tests/integ/`folder](#testsinteg-folder)
  * [Helper modules](#helper-modules-1)
  * [SSM Parameters](#ssm-parameters-1)

Each service is represented by a __folder__ at the root of the repository with a __metadata.yaml__ file. Any folder that does not contain this file is not considered as a service folder. This means that you can retrieve the list of services by running the following command:

```bash
for metafile in */metadata.yaml ;do echo $(dirname $metafile); done
```

On top of that, a service also requires a `template.yaml` file, which contains the [CloudFormation](https://aws.amazon.com/cloudformation/) template that define resources for that service.

## `metadata.yaml`

The __metadata.yaml__ file contains information about the service itself, such as its name, dependencies and feature flags. See the [schema definition](../shared/metadata/schema.yaml) to know what you can use for your service.

## `template.yaml`

The __template.yaml__ is a CloudFormation template containing the resources that will be deployed as part of the service.

You can make sure that the template conforms to the rules by running the lint command from the [toolbox CLI](toolbox.md). This runs [cfn-lint](https://github.com/aws-cloudformation/cfn-python-lint) with a few additional rules (defined in [shared/lint/rules/](../shared/lint/rules/)):

* The template should contains the "Environment" parameter.
* All Lambda functions should use the Python 3.8 runtime.
* All Lambda functions should have a LogGroup matching that function. This ensures control over the retention duration and automatically delete the log group when deleting the function.

It is recommended to use the [Serverless Application Model (SAM)](https://aws.amazon.com/serverless/sam/), as it adds quality of life enhancements to CloudFormation templates for serverless applications, but it is not enforced by a rule. You can use SAM by adding this line in your template:

```yaml
Transform: "AWS::Serverless-2016-10-31"
```

### Capabilities

When deploying the template through CloudFormation, the stack is run with the _CAPABILITY_IAM_ and _CAPABILITY_AUTO_EXPAND_ capabilities (see [the CreateStack API](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_CreateStack.html#API_CreateStack_RequestParameters)). This allow the creation of IAM roles without custom names and using macros in nested stacks.

### API Gateway

When using API Gateway, it is recommended to create a [`resources/openapi.yaml`](#resourcesopenapiyaml) file containing the OpenAPI document for API Gateway.

You can add the following resource in your template to leverage API Gateway:

```yaml
  Api:
    # Create an API Gateway REST API using SAM
    Type: AWS::Serverless::Api
    Properties:
      DefinitionBody:
        # Includes the openapi.yaml file
        Fn::Transform:
          Name: "AWS::Include"
          Parameters:
            Location: "resources/openapi.yaml"
      # Make the endpoint regional, SAM defaults to edge-optimized
      EndpointConfiguration: REGIONAL
      # Sets the default stage name
      StageName: prod
      # Enable X-Ray tracing
      TracingEnabled: true
```

### SSM Parameters

To share resources with other services, you should leverage SSM Parameters. You should also follow the naming convention set in [the conventions document](conventions.md).

For the [API Gateway mentioned above](#api-gateway), you can add the following resource:


```yaml
  ApiUrlParameter:
    Type: AWS::SSM::Parameter
    Properties:
      # Follows the SSM parameter naming convention
      # Replace "your-service" with your service name
      Name: !Sub /ecommerce/${Environment}/your-service/api/url
      Type: String
      # Sets the value to the complete URL
      Value: !Sub "https://${Api}.execute-api.${AWS::Region}.amazonaws.com/prod"

```

## `resources/openapi.yaml`

The __resources/openapi.yaml__ file contains the OpenAPI document for an API Gateway REST API, if you have one in your template. If you don't expose a REST API, you don't need to have this file in your service.

You can use shared schemas from the [shared/resources/schemas.yaml](../shared/resources/schemas.yaml) document. The build command of the [toolbox CLI](toolbox.md) will merge the documents into a single OpenAPI file for API Gateway.

As this document is imported into the CloudFormation template using [`Fn::Include`](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/create-reusable-transform-function-snippets-and-add-to-your-template-with-aws-include-transform.html), you can use CloudFormation functions such as `Fn::Sub`, `Fn::GetAtt`, etc.

### Authorizers

You can add authorizers using the [`x-amazon-apigateway-authtype`](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-swagger-extensions-authtype.html) and [`x-amazon-apigateway-authorizer`](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-swagger-extensions-authorizer.html) in the [`components.securitySchemes`](https://swagger.io/docs/specification/authentication/) of your OpenAPI document.

For example, if you want to add support for IAM credentials:

```yaml
components:
  securitySchemes:
    # Create a scheme named 'AWS_IAM'
    AWS_IAM:
      type: apiKey
      name: Authorization
      in: header
      x-amazon-apigateway-authtype: awsSigv4
```

For a Cognito User Pool:

```yaml
components:
  securitySchemes:
    # Create a scheme named 'UserPool'
    UserPool:
      type: apiKey
      name: Authorization
      in: header
      x-amazon-apigateway-authtype: cognito_user_pools
      x-amazon-apigateway-authorizer:
        type: cognito_user_pools
        providerARNs:
          # Reference to a value in your stack, for example a parameter named 'UserPoolArn'
          - Ref: UserPoolArn
```

You can then use the scheme in your [operations](https://swagger.io/docs/specification/paths-and-operations/) as such:
```yaml
paths:
  /my-iam-path:
    get:
      # ...
      security:
        - AWS_IAM: []
  /my-cognito-path:
    get:
      # ...
      security:
        - UserPool: []
```

### Lambda integrations

To use a Lambda function as the integration for an operation, you should use the [`x-amazon-apigateway-integration`](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-swagger-extensions-integration.html) extension as such:

```yaml
paths:
  /my-lambda-path:
    get:
      # ...
      x-amazon-apigateway-integration:
        httpMethod: "POST"
        type: aws_proxy
        uri:
          # You can use CloudFormation functions such as 'Fn::Sub' in your OpenAPI documents
          Fn::Sub: "arn:${AWS::Partition}:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${GetOrderFunction.Arn}/invocations"

```

### Listener stack

_TODO_

## `resources/events.yaml`

The __resources/events.yaml__ document contains schemas emitted to the EventBridge event bus by your service using the OpenAPI specification as sets in the [EventBridge documentation](https://docs.aws.amazon.com/eventbridge/latest/userguide/eventbridge-schemas.html#eventbridge-schemas-create). Your schemas should be defined in the [`components.schemas`](https://swagger.io/docs/specification/components/) section of the file.

You can use a convenience schema named `EventBridgeHeader` and defined in [`shared/resources/schemas.yaml`](../shared/resources/schemas.yaml) to set up common EventBridge message properties, such as `id`, `version`, `detail`, etc.

For example:

```yaml
components:
  schemas:
    # Replace 'YourServiceEvent' by your event name
    YourServiceEvent:
      # Replace 'your-service' with your service name
      x-amazon-events-source: ecommerce.your-service
      # Replace 'YourServiceEvent' by your event name
      x-amazon-events-detail-type: YourServiceEvent
      description: Event emitted when something happens in your service.
      allOf:
        # Convenience schema containing common EventBridge parameters
        - $ref: "../../shared/resources/schemas.yaml#/EventBridgeHeader"
        - type: object
          properties:
            # Set the details of your event here
            detail:
              # ...
```

## `src/` folder

The __src/__ folders contains the source code of your Lambda functions. The code should not be placed directly into this folder but Lambda functions should have dedicated folders within it.

By convention, each Lambda function should have a dedicated folder, with a __main.py__ file containing a function handler named __handler__. However, this is not enforced.

### Requirements.txt

Within the folder containing a Lambda function code, you can put a `requirements.txt` file. The build command in the [toolbox CLI](toolbox.md) will install packages from that file using pip. Therefore, you can use anything valid for a [pip requirements file](https://pip.readthedocs.io/en/latest/reference/pip_install/#requirements-file-format).

### `ecom` module

As a convenience, you can use the `ecom` python module provided at [shared/src/ecom/](../shared/src/ecom/). To use this module within your function code, add `shared/src/ecom/` in your function's requirements.txt file. From there, you can use `import ecom` in your function code.

## `tests/unit/` folder

The __tests/unit/__ folder should contain unit tests for your Lambda function. By convention, each unit tests should be in a separate folder matching the folder of your Lambda function.

For example, if you have a Lambda function at `src/my_function/`, the unit tests for that function should be stored at `tests/unit/my_function/`. Unit tests are run using [pytest](https://docs.pytest.org/en/latest/).

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

## `tests/integ/` folder

The __tests/integ/__ folder performs integration tests _within the boundaries of your service_ with resources deployed on AWS. Compared to the unit tests, these validate that integration between services are working as expected.

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