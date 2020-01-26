Writing function code
=====================

* [Function folders](#function-folders)
* [CloudFormation resources](#cloudformation-resources)
* [requirements.txt](#requirementstxt)
* [`ecom` module](#ecom-module)
* [Lambda powertools](#lambda-powertools)

## Function folders

Within a service folder, Lambda function code should be stored in a dedicated folder in the `src/` folder. For example, if you have a function `GetItemFunction` in your CloudFormation template, you should create a folder `src/get_item/`.

While there are no strict enforcement on a naming convention, some features from the build command from the [toolbox CLI](toolbox.md), such as [automatic installation of python dependencies](#requirementstxt), will not work if you don't structure the service in this way.

## CloudFormation resources

When using the [Serverless Application Model (SAM)](https://aws.amazon.com/serverless/sam/), you can add a `Globals` section in your template that will contain default propertie values so you don't need to repeat them throughout your template. 

```yaml
Globals:
  Function:
    # Ensures that all functions use the Python 3.8 runtime.
    # Please note that a custom linting rule for `cfn-lint` enforces the use of
    # Python 3.8.
    Runtime: python3.8
    # If all your functions use the same structure with `main.py` containing
    # a handler function called `handler`, you can set the default value as
    # such.
    Handler: main.handler
    # Sets the default timeout to 30 seconds
    Timeout: 30
    # Enable X-Ray tracing
    Tracing: Active
    Environment:
      # All these environment variables will be available in all Lambda functions
      Variables:
        ENVIRONMENT: !Ref Environment
        EVENT_BUS_NAME: !Ref EventBusName
        # Replace 'your-service' with the name of your service
        POWERTOOLS_SERVICE_NAME: your-service
        POWERTOOLS_TRACE_DISABLED: "false"
        LOG_LEVEL: !Ref LogLevel
```

You can then define your function as such:

```yaml
Resources:
  # Put the name of your function here.
  GetItemsFunction:
    Type: AWS::Serverless::Function
    Properties:
      # Put the source folder here.
      CodeUri: src/get_items/
      # You can add additional environment variables as such.
      Environment:
        Variables:
          ITEMS_LIMIT: "20"
      # Even if the OpenAPI document specifies the mapping between operations
      # and Lambda functions, we need to grant access to the Lambda function.
      # This will create a `AWS::Lambda::Permission` resource authorizing the
      # API Gateway to call the Lambda function.
      Events:
        UserApi:
          Type: Api
          Properties:
            Path: /
            Method: GET
            RestApiId: !Ref Api
      # Add the IAM policies here. As a best practice, it is recommended to
      # scope it down to only the actions and resources your function needs.
      # SAM will ensure that Lambda functions have the necessary permissions
      # to write logs to CloudWatch.
      Policies:
        - Version: "2012-10-17"
          Statement:
            - Effect: Allow
              Action: dynamodb:Query
              Resource:
                - !Sub "arn:${AWS::Partition}:dynamodb:${AWS::Region}:${AWS::AccountId}:table/${Table}"
```

Finally, to allow fine-grain control over [CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html) log groups, you should add a LogGroup resource matching the one that your Lambda function will use. This is also enforced by a custom `cfn-lint` rule.

```yaml
  GetItemsLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub "/aws/lambda/${GetItemsFunction}"
      RetentionInDays: !Ref RetentionInDays
```

## `requirements.txt`

Within the folder containing a Lambda function code, you can put a `requirements.txt` file. The build command in the [toolbox CLI](toolbox.md) will install packages from that file using pip. Therefore, you can use anything valid for a [pip requirements file](https://pip.readthedocs.io/en/latest/reference/pip_install/#requirements-file-format).

## `ecom` module

As a convenience, you can use the `ecom` python module provided at [shared/src/ecom/](../shared/src/ecom/). To use this module within your function code, add `shared/src/ecom/` in your function's requirements.txt file. From there, you can use `import ecom` in your function code.

## Lambda powertools

As a best practice, you should use the [AWS Lambda Powertools](https://github.com/awslabs/aws-lambda-powertools/tree/develop/python) module. You can start using it by adding `aws-lambda-powertools` in the [requirements.txt](#requirementstxt) of your Lambda functions.

The example in the [CloudFormation section](#cloudformation-resources) of this document includes examples on how to set up environment variables for the Lambda powertools.

In your function code, you can then add the following to set up the logger and tracer utilities:

```python
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context


logger = logger_setup() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name
```

You can then decorate your function handler as such:

```python
@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler
    """

    # Use the logger to add structured logs
    logger.debug({"message": "Event received", "event": event})

    # Write your code here
    # ...
```

You can also capture [X-Ray subsegments](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html#xray-concepts-subsegments) by decorating other functions within your code as such:

```python
@tracer.capture_method
def my_function(*args):
    """
    Function decorated by the tracer
    """

    # Write your code here
```