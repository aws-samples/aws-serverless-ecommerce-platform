Products service
================

![Products architecture diagram](images/products.png)

## API

See [resources/openapi.yaml](resources/openapi.yaml) for a list of available API paths.

## Events

See [resources/events.yaml](resources/events.yaml) for a list of available events.

## SSM Parameters

This service defines the following SSM parameters:

* `/ecommerce/{Environment}/products/api/arn`: ARN for the API Gateway
* `/ecommerce/{Environment}/products/api/url`: URL for the API Gateway
* `/ecommerce/{Environment}/products/table/name`: DynamoDB table containing the products