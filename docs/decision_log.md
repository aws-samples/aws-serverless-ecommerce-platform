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

## 2019-12-18 SSM Parameters and CloudFormation ImportValues

## 2019-12-18 OpenAPI vs SAM events

## 2019-12-18 SSM Parameter names and separation of environments

## 2020-01-08 Python for tests and Lambda functions

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