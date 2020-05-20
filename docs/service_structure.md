Service structure
=================

At minimum, a service should contain two files: __Makefile__ and __metadata.yaml__. The Makefile contains instructions to build, package, deploy, test a given service using [GNU make](https://www.gnu.org/software/make/). The metadata.yaml file contains information such as dependencies and CloudFormation parameters.

When using one of the [default Makefiles](../shared/makefiles/), there might be other files which will be described throughout this document.

For the list of targets for Makefile, please refer to the [Make targets](make_targets.md) page.

## metadata.yaml

The __metadata.yaml__ files contains information such as its name, dependencies and feature flags. See the schema definition to know what you can use for your service. Here's an example of a metadata file:

```yaml
name: my-service

# These will be used to check whether all dependencies for a service are
# deployed and check if there are any circular dependency. This allows to
# redeploy the entire infrastructure from scratch.
dependencies:
  - products
  - platform

# This section is used for service discovery. See the 'Service discovery' page in the documentation for more information.
parameters:
  EventBusName: /ecommerce/{Environment}/platform/event-bus/name
  ProductsApiArn: /ecommerce/{Environment}/products/api/arn
  ProductsApiUrl: /ecommerce/{Environment}/products/api/url

# Boolean flags regarding a specific service. For example, the pipeline service
# does not support environments, or some services might not support tests.
# This section is optional and the values provided there are the default values.
flags:
  environment: true
  skip-tests: false
```

## template.yaml

_This section is applicable when using one of the [default Makefiles](../shared/makefiles/). If you're using a custom Makefile, you have the freedom to structure this section as you see fit._

The __template.yaml__ file is the CloudFormation template that defines the resources that are part of the service.

## resources/ folder

_This section is applicable when using one of the [default Makefiles](../shared/makefiles/). If you're using a custom Makefile, you have the freedom to structure this section as you see fit._

This folder contains resource files such as OpenAPI document for API Gateway REST APIs or EventBridge event schemas, nested CloudFormation templates, etc.

By convention, the API Gateway REST API document should be named __resources/openapi.yaml__ and the EventBridge event schema documents should be named __resources/events.yaml__. These files are linted automatically as part of the process using the lint command. See the [testing](testing.md) section of the documentation to learn more.

## src/ folder

_This section is applicable when using one of the [default Makefiles](../shared/makefiles/). If you're using a custom Makefile, you have the freedom to structure this section as you see fit._

This section contains the source code of Lambda functions. The code should not be placed directly into this folder but Lambda functions should have dedicated folders within it.

## tests/ folder

_This section is applicable when using one of the [default Makefiles](../shared/makefiles/). If you're using a custom Makefile, you have the freedom to structure this section as you see fit._

The tests/ folder contains unit and integration tests for the service. See the [testing section](testing.md) of the documentation to learn more.