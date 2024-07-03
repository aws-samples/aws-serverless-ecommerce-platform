Platform service
================

![Platform architecture diagram](images/platform.png)

## API

_This service does not expose a REST API_

## Events

_This service does not emit any event_

## SSM Parameters

This service defines the following SSM parameters:

* `/ecommerce/{Environment}/platform/event-bus/name`: Event Bus Name
* `/ecommerce/{Environment}/platform/event-bus/arn`: Event Bus ARN
* `/ecommerce/{Environment}/platform/listener-api/url`: URL for the WebSocket Listener API
