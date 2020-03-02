Frontend service
================

![Frontend architecture diagram](images/frontend.png)

## API

See [resources/api.graphql](resources/api.graphql) for the GraphQL API.

## Events

_None at the moment._

## SSM Parameters

This service defines the following SSM parameters:

* `/ecommerce/{Environment}/frontend/api/arn`: ARN for the GraphQL API
* `/ecommerce/{Environment}/frontend/api/url`: URL of the GraphQL API