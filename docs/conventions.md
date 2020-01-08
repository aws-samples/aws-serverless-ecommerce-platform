Conventions
===========

## Service folder structure

Each service should have the following structure in its folder:

* __/{service}/resources/openapi.yaml__ (optional): File containing the OpenAPI specification. This is optional if the service does not provide an API.
* __/{service}/resources/events.yaml__ (optional): File containing the event schemas for EventBridge in OpenAPI format. This is optional if the service does not emit events.
* __/{service}/src/{function}/__ (optional): Source code for Lambda functions.
* __/{service}/template.yaml__: CloudFormation template for the service.
* __/{service}/tests/integ/__ (optional): Contains integration tests that are run on a deployed infrastructure.

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
