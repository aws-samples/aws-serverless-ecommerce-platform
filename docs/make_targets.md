Make targets
============

## Project-level targets

These targets are part of the [Makefile at the root of this repository](../Makefile).

* __all-$SERVICE__: Lint, build, run unit tests, package, deploy and run integration test for a specific service. You can also run `make all` to run this command against all services.
* __ci-$SERVICE__: Lint, build and run unit tests for a specific service. You can also run `make ci` to run this command against all services.
* __tests-e2e__: Run end-to-end tests using public APIs to validate that the entire platform works as expected.
* __validate__: Check if the necessary tools are installed.
* __setup__: Configure the development environment.
* __activate__: Activate the pyenv virtual environment for Python.
* __requirements__: Install python dependencies for this project.
* __npm-install__: Install node dependencies for this project.
* __bootstrap-pipeline__: Setup all three environments (tests, staging and prod) and the CI/CD pipeline to deploy to production. This also initializes a git repository on [AWS CodeCommit](https://aws.amazon.com/codecommit/) that will be used to trigger the pipeline.

## Service-level target

These targets should be defined in the Makefile of each individual service. You can run the target by running `make $TARGET-$SERVICE` in the root of this project, or `make $TARGET` to run it against all services, e.g. `make tests-unit-all`.

* __artifacts__: Create a zip file containing the template and artifacts for the CI/CD pipeline.
* __build__: Build the resources to deploy the service, such as Lambda functions, OpenAPI specification, CloudFormation templates, etc.
* __check-deps__: Checks if the dependencies of this service are deployed in the target environment.
* __clean__: Remove the build artifacts for the service.
* __deploy__: Deploy/update the service on AWS, usually create/update the CloudFormation stack.
* __lint__: Run linting checks on source code, CloudFormation template, etc.
* __package__: Package and store artifacts in an S3 bucket in preparation for deployment.
* __teardown__: Tear down resources for that services on AWS, usually delete the CloudFormation stack.
* __tests-integ__: Run integration tests against resources deployed on AWS.
* __tests-unit__: Run unit tests locally.

## Environment variables

You can tweak some of the behaviour by using the following environment variables.

* __ENVIRONMENT__: The target environment on AWS on which you want to deploy resources or run integration tests. This default to `dev`.
