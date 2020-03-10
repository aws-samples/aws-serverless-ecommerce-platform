Service structure
=================

* [`Makefile`](#makefile)
  * [`artifacts` target](#artifacts-target)
  * [`build` target](#build-target)
  * [`check-deps` target](#check-deps-target)
  * [`clean` target](#clean-target)
  * [`deploy` target](#deploy-target)
  * [`lint` target](#lint-target)
  * [`package` target](#package-target)
  * [`teardown` target](#teardown-target)
  * [`tests-integ` target](#tests-integ-target)
  * [`tests-unit` target](#tests-unit-target)
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

On top of that, a service also requires a `Makefile` file, which contains the instructions to build the service.

## `Makefile`

The __Makefile__ contains the necessary commands to lint, build, package and deploy services. As each service could work in slightly different way, such as using different languages or deployment methodologies, this gives flexibility to each service to define how to deploy it. For convenience, you can find Makefiles for common scenarios in the [shared/makefiles/](../shared/makefiles/) folder. You can also find a template at [shared/makefiles/empty.mk](../shared/makefiles/empty.mk).

Each Makefile should containing the following targets: [artifacts](#artifacts-target), [build](#build-target), [check-deps](#check-deps-target), [clean](#clean-target), [deploy](#deploy-target), [lint](#lint-target), [package](#package-target), [teardown](#teardown-target), [tests-integ](#tests-integ-target) and [tests-unit](#tests-unit-target).

### `artifacts` target

This target is used by the pipeline to deploy resources into the tests, staging and prod environment.

This target must create a zip file at `${service_dir}/build/artifacts.zip` that contains the CloudFormation template and one [template configuration file](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/continuous-delivery-codepipeline-cfn-artifacts.html) per environment.

The zip file must have the following structure:
* `template.yaml`: CloudFormation template in YAML format.
* `config.{Environment}.json`: The template configuration files, with one file per environment.

_Note_: if you are using the `tools/build cloudformation` script in the [`build` target](#build-target), it will generate these files in `build/artifacts` during the `build`. You can then use the `tools/artifacts cloudformation` script to create the zip file.

### `build` target

This target builds all the resources necessary to deploy resources to AWS, such as code packages of AWS Lambda functions, CloudFormation templates, OpenAPI documents, etc.

By convention, you should build resources inside the `${service_dir}/build/` folder, to prevent accidentally overwriting files in the service folder. This folder is also present in [.gitignore](../.gitignore).

See also the [`clean` target](#clean-target).

### `check-deps` target

This target verifies that the dependencies of the service (as defined in [`metadata.yaml`](#metadatayaml)) are deployed on AWS. If one or multiple dependencies are missing, this should return an error.

### `clean` target

This target removes all artifacts produced by the [`build` target](#build-target) from the service folder.

If you are using the `tools/clean` script, this deletes the `${service_dir}/build/` folder.

### `deploy` target

This target deploys the service on AWS.

### `lint` target

This target analyzes the resources defined for the service for potential bug or stylistic errors. This is executed _before_ the [`build` target](#build-target) and should therefore check resources in the service folder directly (e.g. `${service_dir}/template.yaml` rather than `${service_dir}/build/template.yaml`).

For example, this could check CloudFormation templates using cfn-lint, check Python code for Lambda functions, but also check that OpenAPI documents match the specifications.

This can also run additional checks by defining custom rules. Some of them are enabled by default when using the `tools/lint cloudformation` script. See [shared/lint/rules/](../shared/lint/rules/).

### `package` target

This target packages artifacts and stores them on AWS for deployment if necessary. For example, this could create a zip file for the code of an AWS Lambda function and store it into an Amazon S3 bucket.

This should also update references within the templates, if any.

See how the [aws cloudformation package](https://docs.aws.amazon.com/cli/latest/reference/cloudformation/package.html) command works to learn more.

### `teardown` target

This target tears down resources on AWS.

### `tests-integ` target

This target runs integration tests against resources deployed on AWS, in the environment specified by the `ENVIRONMENT` variable (defaults to `dev`).

### `tests-unit` target

This target runs unit tests against code in the `${service_dir}/build/` folder.

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