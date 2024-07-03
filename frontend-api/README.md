Frontend API service
================

<p align="center">
  <img alt="Frontend architecture diagram" src="images/frontend.png"/>
</p>

## API

See [resources/api.graphql](resources/api.graphql) for the GraphQL API.

## Events

_None at the moment._

## SSM Parameters

This service defines the following SSM parameters:

* `/ecommerce/{Environment}/frontend-api/api/arn`: ARN for the GraphQL API
* `/ecommerce/{Environment}/frontend-api/api/id`: ID of the GraphQL API
* `/ecommerce/{Environment}/frontend-api/api/url`: URL of the GraphQL API