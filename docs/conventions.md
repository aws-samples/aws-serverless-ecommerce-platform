Conventions
===========

* [API standards](#api-standards)
* [Service folder structure](#service-folder-structure)
* [Passing resources across services](#passing-resources-across-services)
* [Python 3](#python-3)

## API standards

API have configuration requirements based on their usage and prefix.

### Service-to-service communication

All API paths for service-to-service communication should be prefixed by `/backend`. For example: `/backend/validate`. Authorization between services should be performed using IAM credentials.

To add the authorizer, you can add [x-amazon-apigateway-auth](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-swagger-extensions-auth.html) in the [operation](https://swagger.io/docs/specification/paths-and-operations/) section of the OpenAPI document. For example:

```yaml
paths:
  /backend/validate:
    post:
      x-amazon-apigateway-auth:
        type: AWS_IAM
```

On the client side, you can use the [aws-requests-auth](https://github.com/DavidMuller/aws-requests-auth) python library to generate a valid signature for the [requests](https://requests.readthedocs.io/en/master/) module. For example:

```python
from urllib.parse import urlparse
from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
import requests


# Gather the domain name and AWS region
url = urlparse(endpoint_url)
region = boto3.session.Session().region_name
# Create the signature helper
auth = BotoAWSRequestsAuth(aws_host=url.netloc,
                           aws_region=region,
                           aws_service='execute-api')
# Send a GET request
response = requests.get(endpoint_url, auth=iam_auth)
```

### Admin-only paths

Admin-only paths should be prefixed by `/admin`. For example: `PUT /admin/{productId}`.

### Public and authenticated requests

All other requests should not use any specific prefix. For example: `GET /{productId}`.

## Service folder structure

Each service should have the following structure in its folder:

* `/{service}/metadata.yaml`: File containing information about the service, such as its name, permissions, dependencies and parameters.
* `/{service}/resources/openapi.yaml` (optional): File containing the OpenAPI specification. This is optional if the service does not provide an API.
* `/{service}/resources/events.yaml` (optional): File containing the event schemas for EventBridge in OpenAPI format. This is optional if the service does not emit events.
* `/{service}/src/{function}/` (optional): Source code for Lambda functions. This is optional if the service does not provide Lambda functions or include the code in the template itself.
* `/{service}/template.yaml`: CloudFormation template for the service.
* `/{service}/tests/integ/` (optional): Contains integration tests that are run on a deployed infrastructure.
* `/{service}/tests/unit/{function}/` (optional): Contains unit tests that are run locally.

## Passing resources across services

Passing resources such as Amazon API Gateway URLs, SNS topics, etc. across services must be done through SSM Parameters.

SSM Parameter names should follow this convention: `/ecommerce/{environment}/{serviceName}/{resourceName}/{type}`. For example:

```
/ecommerce/dev/users/user-pool/arn
/ecommerce/prod/orders/api/url
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
      Name: !Sub /ecommerce/${Environment}/users/user-pool/arn
      Type: String
      Value: !GetAtt UserPool.Arn
```

To use resources in your service, you should use CloudFormation parameters. For example:

```yaml
Parameters:
  UserPoolArn:
    Type: AWS::SSM::Parameter::Value<String>
    Description: Cognito User Pool ARN
```

To minimize the risk of errors when using multiple environments, you should not set a default value to the parameter. You should instead add the parameter in the `metadata.yaml` file for automatic transformation:

```yaml
parameters:
  # Note the lack of '$' here
  UserPoolArn: /ecommerce/{Environment}/users/user-pool/arn
```

## Python 3

Services should use [Python 3.8](https://docs.python.org/3/whatsnew/3.8.html) whenever possible, both for tests and for Lambda function code. In the same way, internal tools should be made using Python 3.8.

Tests should be written for [pytest](https://docs.pytest.org/en/latest/).