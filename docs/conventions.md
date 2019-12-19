Conventions
===========

## Passing resources across services

Passing resources such as Amazon API Gateway URLs, SNS topics, etc. across services must be done through SSM Parameters.

SSM Parameter names should follow this convention: `/ecommerce/{serviceName}/{resourceName}/{type}`. For example:

```
/ecommerce/platform/user-pool/arn
/ecommerce/orders/api/url
```

To use resources in your service, you should use CloudFormation parameters. For example:

```
Parameters:
  UserPoolArn:
    Type: AWS::SSM::Parameter::Value<String>
    Description: Cognito User Pool ARN
    Default: /ecommerce/platform/user-pool/arn
```
