Toolbox
=======

There is an automation script called `tools/toolbox` that allow developers to perform actions such as run test cases, build a service and deploy it into their AWS sandbox account.

## Usage

You use the toolbox script by providing an action and the service that you want to target as such:

```bash
tools/toolbox $SERVICE_NAME $ACTION

# For example:
tools/toolbox products build
tools/toolbox platform deploy
```

You can also provide a chain of actions to perform. For example, if you want to build, package, deploy and run integration tests on the __products__ service:

```bash
tools/toolbox products build package deploy tests-integ
```

## Supported commands

The following commands are supported: `ci`, `all`, `build`, `clean`, `deploy`, `lint`, `metadata`, `package`, `tests-func` and `tests-integ`.

### `ci` command

The __ci__ command runs `display`, `lint`, `clean`, `build` and `tests-unit`.

### `display` command

The __display__ command runs `display-metadata`, `display-parameters` and `display-tags`.

### `all` command

The __all__ command runs `display`, `lint`, `clean`, `build`, `tests-unit`, `check-deps`, `package`, `deploy` and `tests-integ`.

### `build` command

The __build__ command copies files from the `src/` and `resources/` folders of a service as well as `template.yaml` into a `build/` folder, transforms the OpenAPI specifications and install required Python packages in the Lambda folders.

It installs Python packages by looking at the `src/{function}/requirements.txt` file.

### `check-deps` command

The __check-deps__ command checks if all dependencies of the service are deployed in the environment.

### `clean` command

The __clean__ command deletes the `build/` folder of a service.

### `deploy` command

The __deploy__ command deploys the service into the developer's sandbox AWS account.

It will take a CloudFormation template at `build/template.out` in the service's directory and deploys it to AWS using the [aws cloudformation deploy](https://docs.aws.amazon.com/cli/latest/reference/cloudformation/deploy/index.html) command.

_Please note that you need to run the __package__ command beforehand._

### `display-metadata` command

The __display-metadata__ command displays metadata information about the service.

### `display-parameters` command

The __display-parameters__ command displays the parameters that will be used to deploy the service using CloudFormation.

### `display-tags` command

The __display-tags__ command displays the tags that will be used to deploy the service using CloudFormation.

### `lint` command

The __lint__ command runs lint checks against the resources in the service.

Currently, it supports CloudFormation template at `template.yaml` and Lambda source code in the `src` folder.

### `package` command

The __package__ commands packages code and other artifacts, upload them to an S3 bucket in the developer's sandbox AWS account, and create a CloudFormation template that can be deployed by the __deploy__ command.

It will take a CloudFormation template at `build/template.yaml` in the service's directory and creates a new template named `build/template.out` using the [aws cloudformation package](https://docs.aws.amazon.com/cli/latest/reference/cloudformation/package.html) command.

_Please note that you need to run the __build__ command beforehand._

### `tests-integ` command

The __tests-integ__ command runs integration tests on a service deployed to AWS.

This command checks for an SSM Parameter named `/ecommerce/{service}/environment` and checks that its value is not _"prod"_.

Integration tests are found in the `tests/integ/` folder of a service. See [conventions](conventions.md).

_Please note that you need to run the __deploy__ command beforehand._

### `tests-unit` command

The __tests-unit__ command runs unit tests against the source of Lambda functions on the local machine.

Unit tests are found in the `tests/unit/` folder of a service. See [conventions](conventions.md).

_Please note that you need to run the __build__ command beforehand._