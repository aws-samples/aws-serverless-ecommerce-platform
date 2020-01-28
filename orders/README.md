Orders service
==============

![Orders architecture diagram](images/orders.png)

## API

See [resources/openapi.yaml](resources/openapi.yaml) for a list of available API paths.

## Events

See [resources/events.yaml](resources/events.yaml) for a list of available events.

## SSM Parameters

This service defines the following SSM parameters:

* `/ecommerce/{Environment}/orders/api/url`: URL for the API Gateway