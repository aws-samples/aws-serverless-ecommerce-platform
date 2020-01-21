"""
Custom rules for cfn-lint
"""


import copy
import logging
from cfnlint.rules import CloudFormationLintRule, RuleMatch


LOGGER = logging.getLogger(__name__)


class MandatoryParametersRule(CloudFormationLintRule):
    """
    Check for Mandatory CloudFormation Parameters
    """

    id = "E9000"
    shortdesc = "Mandatory Parameters"
    description = "Ensuring that mandatory parameters are present"
    tags = ["ecommerce", "parameters"]

    _mandatory_parameters = ["Environment"]
    _message = "Missing parameter '{}'"

    def match(self, cfn):
        """
        Match missing mandatory parameters
        """

        mandatory_parameters = copy.deepcopy(self._mandatory_parameters)

        for key in cfn.get_parameters().keys():
            if key in mandatory_parameters:
                mandatory_parameters.remove(key)

        return [
            RuleMatch(["Parameters"], self._message.format(param))
            for param in mandatory_parameters
        ]


class Python38Rule(CloudFormationLintRule):
    """
    Check for Python3.8 usage
    """

    id = "E9001"
    shortdesc = "Python3.8 Lambda usage"
    description = "Ensure that Python3.8 is used by all Lambda functions"
    tags = ["ecommerce", "lambda"]

    _runtime = "python3.8"
    _message = "Function is using {} runtime instead of {}"

    def match(self, cfn):
        """
        Match against Lambda functions not using python3.8
        """

        matches = []

        for key, value in cfn.get_resources(["AWS::Lambda::Function"]).items():
            if value.get("Properties").get("Runtime") != self._runtime:
                matches.append(RuleMatch(
                    ["Resources", key],
                    self._message.format(value.get("Properties").get("Runtime"), self._runtime)
                ))

        return matches