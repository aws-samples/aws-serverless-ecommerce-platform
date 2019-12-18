AWS Serverless Ecommerce Platform
=================================

The __Serverless Ecommerce Platform__ is a sample implementation of a serverless backend for an e-commerce website. Functionalities are split across multiple micro-services that communicate either through asynchronous messages over [Amazon EventBridge](https://aws.amazon.com/eventbridge/) or over synchronous APIs.

## Backend services

|  Services  | Description                               |
|------------|-------------------------------------------|
| Users      | Provides user management, authentication and authorization. |
| Products   | Source of truth for products information. |
| Orders     | Manages order creation and status.        |
| Warehouse  | Manages inventory and packaging orders.   |
| Delivery   | Manages shipping and tracking packages.   |
| Payment    | Manages payment collection and refunds.   |

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
