Conventions
===========

* [API standards](#api-standards)
* [Events naming](#events-naming)
* [Passing resources across services](#passing-resources-across-services)
* [Python 3](#python-3)
* [Service folder structure](#service-folder-structure)


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
iam_auth = BotoAWSRequestsAuth(aws_host=url.netloc,
                           aws_region=region,
                           aws_service='execute-api')
# Send a GET request
response = requests.get(endpoint_url, auth=iam_auth)
```

### Admin-only paths

Admin-only paths should be prefixed by `/admin`. For example: `PUT /admin/{productId}`.

### Public and authenticated requests

All other requests should not use any specific prefix. For example: `GET /{productId}`.

## Events naming

When creating new events, services should use the following naming convention for detail-types.

### `[Resource]Created`

This event results from the creation of a specific resource owned by the service. The detail must contain all the values of that resource.

### `[Resource]Deleted`

This event results from the deletion of a specific resource owned by the service. The detail must contain the resource identifier (e.g. `resourceId`) and can contain all the other information.

### `[Resource]Modified`

This event results from the modification of a specific resource owned by the service. The detail must contain three parameters: `old`, `new` and `changed`.

* `old` should contain the old values of the resource.
* `new` should contain the new values.
* `changed` should contain an array of parameter names that were changed. For nested parameters, this could be either the root parameter name (`rootParam`), or the list of parameters separated by dots (`rootParam.childParam`).
  If the modification concerns an element in an array, the array itself should be referenced (`rootParam.arrayParam`), not the specific index (not `rootParam.arrayParam[3]`).

For example:

```json
{
  "source": "ecommerce.products",
  "detail-type": "ProductChanged",
  "resources": ["c60d29c0-434e-4efc-b893-1c604d0718cc"],
  "detail": {
    "old": {
      "productId": "c60d29c0-434e-4efc-b893-1c604d0718cc",
      "name": "Sample Product",
      "price": 500,
      "package": {
        "width": 500,
        "height": 300,
        "length": 200,
        "weight": 1000
      }
    },
    "new": {
      "productId": "c60d29c0-434e-4efc-b893-1c604d0718cc",
      "price": 500,
      "package": {
        "width": 500,
        "height": 300,
        "length": 350,
        "weight": 1000
      }
    },
    "changed": [
      "price",
      "package.length"
    ]
  }
}
```

### `[Operation]Failed`

This event results from the failure to perform an operation that is owned by the service. The detail should contain the resource identifier on which the operation applies.

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

Services should use [Python 3.9](https://docs.python.org/3/whatsnew/3.9.html) whenever possible, both for tests and for Lambda function code. In the same way, internal tools should be made using Python 3.9.

Tests should be written for [pytest](https://docs.pytest.org/en/latest/).

## Service folder structure

Each service should have the following structure in its folder:

* `/{service}/Makefile`: File containing the build instructions for the service.
* `/{service}/metadata.yaml`: File containing information about the service, such as its name, permissions, dependencies and parameters.
* `/{service}/resources/openapi.yaml` (optional): File containing the OpenAPI specification. This is optional if the service does not provide an API.
* `/{service}/resources/events.yaml` (optional): File containing the event schemas for EventBridge in OpenAPI format. This is optional if the service does not emit events.
* `/{service}/src/{function}/` (optional): Source code for Lambda functions. This is optional if the service does not provide Lambda functions or include the code in the template itself.
* `/{service}/template.yaml`: CloudFormation template for the service.
* `/{service}/tests/integ/` (optional): Contains integration tests that are run on a deployed infrastructure.
* `/{service}/tests/unit/{function}/` (optional): Contains unit tests that are run locally.
