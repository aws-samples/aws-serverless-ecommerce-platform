"""
Custom rules for cfn-lint
"""


import copy
from cfnlint.rules import CloudFormationLintRule, RuleMatch


class MandatoryParametersRule(CloudFormationLintRule):
    """
    Checks for Mandatory CloudFormation Parameters
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
