Service structure
=================

* `Makefile`(#makefile)
* [`metadata.yaml`](#metadatayaml)
* [`template.yaml`](#templateyaml)
  * [Capabilities](#capabilities)
  * [API Gateway](#api-gateway)
  * [SSM Parameters](#ssm-parameters)
* [`resources/openapi.yaml`](#resourcesopenapiyaml)
  * [Authorizers](#authorizers)
  * [Lambda integrations](#lambda-integrations)
* [`resources/events.yaml`](#resourceseventsyaml)
* [`src/` folder](#src-folder)
* [`tests/unit/` folder](#testsunit-folder)
* [`tests/integ/`folder](#testsinteg-folder)

Each service is represented by a __folder__ at the root of the repository with a __metadata.yaml__ file. Any folder that does not contain this file is not considered as a service folder. This means that you can retrieve the list of services by running the following command:

```bash
for metafile in */metadata.yaml; do echo $(dirname $metafile); done
```

On top of that, a service also requires a `template.yaml` file, which contains the [CloudFormation](https://aws.amazon.com/cloudformation/) template that define resources for that service.

## `Makefile`

The __Makefile__ contains the necessary commands to lint, build, package and deploy services. As each service could work in slightly different way, such as using different languages or deployment methodologies, this gives flexibility to each service to define how to deploy it. For convenience, you can find Makefiles for common scenarios in the [shared/makefiles/](../shared/makefiles/) folder. You can also find a template at [shared/makefiles/empty.mk](../shared/makefiles/empty.mk).

Each Makefile should containing the following targets: build, check-deps, clean, deploy, lint, package, teardown, tests-integ and tests-unit.

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

See the [function code document](function_code.md) for more information for more information about writing Lambda functions.

## `tests/unit/` folder

The __tests/unit/__ folder should contain unit tests for your Lambda function. By convention, each unit tests should be in a separate folder matching the folder of your Lambda function.

For example, if you have a Lambda function at `src/my_function/`, the unit tests for that function should be stored at `tests/unit/my_function/`. Unit tests are run using [pytest](https://docs.pytest.org/en/latest/).

See [the testing guide](testing.md#unit-tests) for more information about writing unit tests.

## `tests/integ/` folder

The __tests/integ/__ folder performs integration tests _within the boundaries of your service_ with resources deployed on AWS. Compared to the unit tests, these validate that integration between services are working as expected.

See [the testing guide](testing.md#integration-tests) for more information about writing integration tests.