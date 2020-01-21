import collections
import importlib
import sys
import os


def context():
    context_tuple = collections.namedtuple("context", [
        "function_name",
        "memory_limit_in_mb",
        "invoked_function_arn",
        "aws_request_id"
    ])

    context = context_tuple(
        "FUNCTION_NAME",
        1024,
        "INVOKED_FUNCTION_ARN",
        "AWS_REQUEST_ID"
    )

    return context


def lambda_module(request):
    """
    Main module of the Lambda function

    This also load environment variables and the path to the Lambda function
    prior to loading the module itself.

    To use this within a test module, do:

        from fixtures import lambda_module
        lambda_module = pytest.fixture(scope="module", params=[{
            "function_dir": "function_dir",
            "module_name": "main",
            "environ": {
                "ENVIRONMENT": "test",
                "EVENT_BUS_NAME": "EVENT_BUS_NAME",
                "POWERTOOLS_TRACE_DISABLED": "true"
            }
        }])(lambda_module)
    """

    # Inject environment variables
    backup_environ = {}
    for key, value in request.param.get("environ", {}).items():
        if key in os.environ:
            backup_environ[key] = os.environ[key]
        os.environ[key] = value

    # Add path for Lambda function
    sys.path.insert(0, os.path.join(os.environ["ECOM_BUILD_DIR"], "src", request.param["function_dir"]))

    # Save the list of previously loaded modules
    prev_modules = list(sys.modules.keys())

    # Return the function module
    module = importlib.import_module(request.param["module_name"])
    yield module

    # Delete newly loaded modules
    new_keys = list(sys.modules.keys())
    for key in new_keys:
        if key not in prev_modules:
            del sys.modules[key]

    # Delete function module
    del module

    # Remove the Lambda function from path
    sys.path.pop(0)

    # Restore environment variables
    for key in request.param.get("environ", {}).keys():
        if key in backup_environ:
            os.environ[key] = backup_environ[key]
        else:
            del os.environ[key]