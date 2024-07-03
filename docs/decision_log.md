Decision log
============

This file is meant to capture all the architectural decisions that were made in this project and why. In many cases, there are no obvious right answers and we have to make a decision with multiple options.

None of these decisions are set in stone, unless the engineering effort to revert it is too great. We should also strive to make decisions that are easy to revert quickly, while spending more time on the other decisions. See [Amazon's 1997 letter to its shareholders](https://www.sec.gov/Archives/edgar/data/1018724/000119312516530910/d168744dex991.htm):

> Some decisions are consequential and irreversible or nearly irreversible – one-way doors – and these decisions must be made methodically, carefully, slowly, with great deliberation and consultation. If you walk through and don’t like what you see on the other side, you can’t get back to where you were before. We can call these Type 1 decisions. But most decisions aren’t like that – they are changeable, reversible – they’re two-way doors. If you’ve made a suboptimal Type 2 decision, you don’t have to live with the consequences for that long. You can reopen the door and go back through. Type 2 decisions can and should be made quickly by high judgment individuals or small groups.

## 2019-12-18 EventBridge as event bus

## 2019-12-18 Mono-repo approach

This decision is more of a consequence of the purpose of this project. As this project is mostly meant to showcase what a serverless implementation of an e-commerce backend with micro-services looks like, discoverability is an important factor.

Two alternatives were considered:

* A single repository containing every micro-services, shared resources, tools, documentation, etc.
* One repository per micro-service, one for shared resources, tooling, infrastructure, etc.

Having a single repository is easier to share, as one only need to share a single link and people can see all the resources for that project. This is also easier to maintain regarding permissions, communications, etc.

However, the mono-repo approach is not fundamental to this project and other design decisions should strive to work for both mono- and poly-repo approaches. For example, the `shared` folder could be provided as an external library, loaded into the build environment, etc. Same thing for the `tools` folder.

## 2019-12-18 SSM Parameters vs CloudFormation ImportValues

With multiple services each deployed using different CloudFormation stacks, we need a way to share resource references between services, such as API Gateway URL, EventBridge event bus name, etc.

As these values change infrequently, we can limit ourselves to only load these values at deployment time, rather than checking for every Lambda function invocation. This means that the SSM Parameter store and CloudFormation ImportValues are two natural choices for this. Both allow references directly in the CloudFormation stack, rather than loading and passing parameter values to the stack.

For ImportValue, this is done by using `Outputs` in the template creating the reference, and `!ImportValue` in the templates that need to access that resource.

For SSM Parameter, this is done by creating a new resource and using template parameters as such:

```yaml
Parameters:
  # Load value from an SSM Parameter
  UserPoolArn:
    Type: AWS::SSM::Parameter::Value<String>
    Description: Cognito User Pool ARN
    Default: /ecommerce/dev/platform/user-pool/arn

Resources:
  # Create a new SSM Parameter
  UserPoolArnParameter:
    Type: AWS::SSM::Parameter
    Properties:
      Name: !Sub /ecommerce/${Environment}/platform/user-pool/arn
      Type: String
      Value: !GetAtt UserPool.Arn
```

_TODO_

## 2019-12-18 OpenAPI vs SAM events

When creating an API Gateway and associating paths to Lambda functions, SAM (Serverless Application Model) provides a lot of convenience. We can simply create the functions and associate with the right path, authorization model, etc. as such:

```yaml
Resources:
  MyFunction:
    Type: AWS::Serverless::Function
    Properties:
      #...
      Events:
        Api:
          Type: Api
          Properties:
            Path: /my/path
            Method: GET
```

When providing the OpenAPI specification instead, we need to add the OpenAPI specification for that path and add API Gateway-specific extensions on top of defining Lambda functions in the CloudFormation template. However, from a documentation and collaboration approach, using OpenAPI directly has several benefits.

We can create an OpenAPI document and share it with other teams before building the service itself. While there might be differences between the initial document and released version, it's easier to discuss about the contract itself with the future consumers of that API.

We can also create a shared library of schemas for common object types, such as products, addresses, etc. that can be used by multiple services.

On the topic of schemas, SAM templates do not provide a built-in way to define the schema accepted or sent by a specific service, which means that services will need to add that manually in their document or build another method to share schemas.

As such, every service that plan on using API Gateway should provide an OpenAPI document describing the paths and schemas related to that API.

## 2020-01-08 SAM CLI vs custom script

As this project uses [SAM](https://github.com/awslabs/serverless-application-model) for defining infrastructure as code, it could be interesting to use the [SAM CLI](https://github.com/awslabs/aws-sam-cli) to manage building, packaging and deploying the different services.

However, to ensure that every developers follow the same standard, providing an overlay tool can be beneficial. Such a tool can also offer functionalities specific to the project or that do not exist in SAM CLI, such as:

* merging OpenAPI documents from multiple files for API Gateway
* automate testing for both Lambda functions and the service as a whole
* enforce security rules (e.g. IAM permissions)

As every service should provide tests and OpenAPI documents that are used in a standardized way, it's better to build a tool (that could leverage SAM CLI) that will provide these functionalities.

## 2020-01-08 Python for tests and Lambda functions

Multiple languages were considered for the code part of this project. As the point of this project is not to showcase how to build serverless micro-services _in a specific language_, it is better to pick a language that a lot of people are comfortable with or that is easy to understand.

According to StackOverflow's survey, Python is used by _X%_ of developers in professional setting. Furthermore, Python's syntax is relatively easy to catch on.

## 2020-01-10 Capturing events on the event bus for non-prod environments

Some integration tests within the boundaries of a service should capture events sent to the EventBridge event bus to ensure that actions emit events according to the contracts set in `{service}/resources/events.yaml`.

To do so, the simplest way is to add a rule that captures all events from a service (using `{"source": ["ecommerce.${Service}"]}` for the rule) and add an SQS queue as target. Developers and automated tests can listen to the SQS queue and check if events are produced as expected.

To deploy the rule and queue, there are three viable options:

* Using the AWS SDK (boto3) and deploy/teardown when running the tests
* Using a CloudFormation stack and deploy/teardown when running the tests
* Using a CloudFormation stack an deploy/teardown at the same time as the non-prod environment

Using the AWS SDK over CloudFormation makes things unecessary brittles and requires to add lots of logic in the test cases. Therefore, CloudFormation is preferred here for the increased availability, even if it means it increases time.

Between deploying the stack for each test case and at service deployment time, it's a trade-off between keeping potentially unecessary resources and time to run the tests. As the development, test and staging environments are meant to test that services are behaving as expected, we should expect that the listener stack will be frequently used in these environments. Therefore, it's probably better to keep it permanently in the non-prod environments.

We can easily revert that decision by removing it from the CloudFormation template (in `{service}/template.yaml`) and add a setup and teardown in the test cases.

## 2020-02-27 __Delivery service__: fetching order information synchronously or asynchronously

The delivery service needs to create a delivery request when the warehouse service sends a `PackageCreated` event onto the event bus. This event does not need to contain the address for the order. However, the delivery service needs to have the address to perform a delivery.

There are two options to solve that problem:

* The delivery service listens for events from the orders service.
* The delivery service queries the order service through an API call to retrieve the delivery address.

In the first case, this means that the delivery service needs to listen for all potential operations: not only `OrderCreated`, but also `OrderModified` and `OrderCancelled`. Before a package is created, the user could potentially change the delivery address and we need to take that into account, thus listening to all `OrderModified` events where the address is changed to ensure that the package is shipped to the right address. Orders could also be cancelled before packaging or the warehouse service could fail to create a package. The delivery service would need to read these events to clean up the database.

In the second case, this creates a synchronous dependency to the orders service, which means that the service could fail to create a delivery request if the orders service is not available. However, these failures can be retried as the function is triggered by an asynchronous event and can have an SQS dead letter queue using [Lambda destinations](https://aws.amazon.com/blogs/compute/introducing-aws-lambda-destinations/).

For this case, the second option is preferred, as it has retriable errors and is much simpler to implement.

This decision can also be reverted by implementing listeners for the orders and other warehouse events. However, as we cannot be sure if any order is missing from the database, changing course would require a one-time operation to synchronise addresses with the orders database.

## 2020-03-01 Using Makefiles to build services

At the beginning, this project used a bespoke python script (at `tools/toolbox`). However, this limited the potential for each service to use different tools and methodologies based on their need. If different teams are building each service, this can clauses slow downs if service teams have to wait for a centralized team to build new capabilities in the script.

For example, all services have been built with CloudFormation up to this point, but if a team decides to build a service using CDK instead, it will either have to wait for the tooling team or build capacities in that scripts (in a polyrepo approach, that often means a pull request and waiting for approval.

In the shared service, there is a [folder containing sample Makefiles](../shared/makefiles/), which acts as a paved road for service teams that are happy to build using a standardized methodology, but they are also free to build their own tools and customize the Makefile to their needs.