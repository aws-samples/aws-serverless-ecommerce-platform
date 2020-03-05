Orders service
==============

<p align="center">
    <img alt="Orders architecture diagram" src="images/orders.png"/>
</p>

## API

See [resources/openapi.yaml](resources/openapi.yaml) for a list of available API paths.

## Events

See [resources/events.yaml](resources/events.yaml) for a list of available events.

## SSM Parameters

This service defines the following SSM parameters:

* `/ecommerce/{Environment}/orders/api/url`: URL for the API Gateway
* `/ecommerce/{Environment}/orders/api/arn`: ARN for the API Gateway
* `/ecommerce/{Environment}/orders/create-order/arn`: ARN for the Create Order Lambda Function