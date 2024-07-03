Service-to-service communication
================================

Services can perform four basic operations in the context of service-to-service communication: query, command, emit and react.

A service __queries__ another when it needs to retrieve information synchronously from that service but this does not result in any state modification. For example, the _delivery_ service querying the _orders_ service to retrieve the delivery address for a given order, or the _orders_ service querying the _products_ service to validate the list of products in an order creation request.

A service sends a __command__ to another service when it needs that other service to perform an action and needs to know immediately if it happened. For example, the _payment_ service sends a command to _payment-3p_ to process a payment. If this fails, the _payment_ service need to retry or alert.

A service __emits__ an event when it needs to propagate that something happened but does not care about what other services do with this information. For example, when an order is created, the _orders_ service is not responsible for making sure that the _warehouse_ service processes that event correctly, but the latter needs to know that this happened to create a packaging request.

Finally, a service __reacts__ to an event when it listens and processes an event from another service.

The first two operations (query and command) are often __synchronous__ as they require an immediate response from the other service, while the latter two are __asynchronous__.

By using asynchronous messaging whenever possible, we decouple services from any availability and latency issues. A service that emits an event should not be responsible to track which services need to receive that event and whether they processed it correctly. For this reason, the platform leverages [Amazon EventBridge](eventbridge.md) heavily. A service will send an event to EventBridge, which uses rules and targets to know where to route events.