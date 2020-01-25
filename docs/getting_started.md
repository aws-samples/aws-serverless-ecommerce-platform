Getting started
===============

## Setup the development environment

To set up the development environment, you will need to install __pyenv__ on your computer. You can find installation instruction at [https://github.com/pyenv/pyenv#installation](https://github.com/pyenv/pyenv#installation).

When __pyenv__ is installed, you can run `make setup` to configure the Python environment for this project, including development tools and dependencies.

Additionally, you will need to install __speccy__ for building specific services. __Speccy__ is used to merge OpenAPI definitions together for API Gateway. You can find installation instruction at [https://github.com/wework/speccy#setup](https://github.com/wework/speccy#setup).

## Deploy the infrastructure on AWS

Deploying the infrastructure with a CI/CD pipeline on AWS will create a new repository in [AWS CodeCommit](https://aws.amazon.com/codecommit/). Please ensure that you have:

* [Configured the AWS CLI on your machine](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
* [Configured Git to use the AWS credential helper](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-https-unixes.html)

Once this is done, you can run `make bootstrap` which will deploy a platform stack in the various environments, the CI/CD pipeline and seed the CodeCommit repository with the latest commit from this repository. This will trigger the pipeline, which will build the other services.

When you want to push modifications to AWS, you can run `git push aws HEAD:master`, which will push the latest commit from the current branch to the master branch in the CodeCommit repository.

## Creating or modifying a service

To read how you can create a new service or modify an existing one, please read the [service structure documentation](service.md)