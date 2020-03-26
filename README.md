AWS Serverless Ecommerce Platform
=================================

__Status__: _Work-in-progress. Please create issues or pull requests if you have ideas for improvement._

The __Serverless Ecommerce Platform__ is a sample implementation of a serverless backend for an e-commerce website. Functionalities are split across multiple micro-services that communicate either through asynchronous messages over [Amazon EventBridge](https://aws.amazon.com/eventbridge/) or over synchronous APIs.

<p align="center">
  <img src="docs/images/flow.png" alt="High-level flow across microservices"/>
</p>

## Getting started

To install the necessary tools and deploy this in your own AWS account, see the [getting started](docs/getting_started.md) guide in the documentation section.

## Architecture

### High-level architecture architecture

This is a high-level view of how the different microservices interact with each other. Each service folder contains anarchitecture diagram with more details for that specific service.

<p align="center">
  <img src="docs/images/architecture.png" alt="High-level architecture diagram"/>
</p>

### Backend services

|  Services  | Description                               |
|------------|-------------------------------------------|
| [users](users/) | Provides user management, authentication and authorization. |
| [products](products/) | Source of truth for products information. |
| [orders](orders/) | Manages order creation and status. |
| [warehouse](warehouse/) | Manages inventory and packaging orders. |
| [delivery](delivery/) | Manages shipping and tracking packages. |
| [delivery-pricing](delivery-pricing/) | Pricing calculator for deliveries. |
| [payment](payment/) | Manages payment collection and refunds. |
| [payment-3p](payment-3p/) | Simulates a third party payment system. |

### Frontend service

|  Services  | Description                               |
|------------|-------------------------------------------|
| [frontend-api](frontend-api/) | User-facing API for interacting with the services. |

### Infrastructure services

|  Services  | Description                               |
|------------|-------------------------------------------|
| [pipeline](pipeline/) | CI/CD pipeline for deploying the resources in production. |
| [platform](platform/) | Core platform resources for deploying backend services. |

### Shared resources

| Name       | Description                               |
|------------|-------------------------------------------|
| [docs](docs/) | Documentation application for all services. |
| [shared](shared/) | Shared resources accessible for all services, such as common CloudFormation templates and OpenAPI schemas. |
| [tools](tools/) | Tools used to build services.             |


## Documentation

See the [docs](docs/) folder for the documentation.

## Contributing

See the [contributing](CONTRIBUTING.md) and [getting started](docs/getting_started.md) documents to learn how to contribute to this project.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
