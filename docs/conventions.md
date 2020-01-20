Conventions
===========

* [API standards](#api-standards)
* [Service folder structure](#service-folder-structure)
* [Passing resources across services](#passing-resources-across-services)
* [Python 3](#python-3)

## API standards

_TODO_

## Service folder structure

Each service should have the following structure in its folder:

* __/{service}/metadata.yaml__: File containing information about the service, such as its name, permissions and dependencies.
* __/{service}/resources/openapi.yaml__ (optional): File containing the OpenAPI specification. This is optional if the service does not provide an API.
* __/{service}/resources/events.yaml__ (optional): File containing the event schemas for EventBridge in OpenAPI format. This is optional if the service does not emit events.
* __/{service}/src/{function}/__ (optional): Source code for Lambda functions. This is optional if the service does not provide Lambda functions or include the code in the template itself.
* __/{service}/template.yaml__: CloudFormation template for the service.
* __/{service}/tests/integ/__ (optional): Contains integration tests that are run on a deployed infrastructure.
* __/{service}/tests/unit/{function}/__ (optional): Contains unit tests that are run locally.

## Passing resources across services

Passing resources such as Amazon API Gateway URLs, SNS topics, etc. across services must be done through SSM Parameters.

SSM Parameter names should follow this convention: `/ecommerce/{serviceName}/{resourceName}/{type}`. For example:

```
/ecommerce/platform/user-pool/arn
/ecommerce/orders/api/url
```

Here is how to create SSM parameters for your resources in CloudFormation:

```yaml
Resources:
  UserPool:
    Type: AWS::Cognito::UserPool
    Properties:
      # ...

  UserPoolArnParameter:
    Type: AWS::SSM::Parameter
    Properties:
      Name: /ecommerce/platform/user-pool/arn
      Type: String
      Value: !GetAtt UserPool.Arn
```

To use resources in your service, you should use CloudFormation parameters. For example:

```yaml
Parameters:
  UserPoolArn:
    Type: AWS::SSM::Parameter::Value<String>
    Description: Cognito User Pool ARN
    Default: /ecommerce/platform/user-pool/arn
```

## Python 3

Services should use [Python 3.8](https://docs.python.org/3/whatsnew/3.8.html) whenever possible, both for tests and for Lambda function code. In the same way, internal tools should be made using Python 3.8.

Tests should be written for [pytest](https://docs.pytest.org/en/latest/).