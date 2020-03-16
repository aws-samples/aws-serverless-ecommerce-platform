Payment service
===============

<p align="center">
    <img alt="Payment architecture diagram" src="images/payment.png"/>
</p>

## API

See [resources/openapi.yaml](resources/openapi.yaml) for a list of available API paths.

## Events

_This service does not publish events._

## SSM Parameters

This service defines the following SSM parameters:

* `/ecommerce/{Environment}/payment/api/url`: URL for the API Gateway
* `/ecommerce/{Environment}/payment/api/arn`: ARN for the API Gateway
