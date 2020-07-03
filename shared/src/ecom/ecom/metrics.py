"""
Helper functions for working with metrics
"""


import datetime
import json
import os
from typing import List, Optional, Union
from aws_lambda_powertools.tracing import Tracer


__all__ = ["log_metrics"]


ENVIRONMENT = os.environ["ENVIRONMENT"]
tracer = Tracer() # pylint: disable=invalid-name


@tracer.capture_method
def log_metrics(namespace: str, metric_names: Union[str, List[str]], metric_values: Union[int, List[int]]) -> None:
    """
    Log custom metrics
    """

    if isinstance(metric_names, str):
        metric_names = [metric_names]
    if isinstance(metric_values, int):
        metric_values = [metric_values]

    assert len(metric_names) <= len(metric_values)

    metrics = {metric_names[i]: metric_values[i] for i in range(len(metric_names))}
    metrics["environment"] = ENVIRONMENT
    metrics["_aws"] = {
        # Timestamp is in milliseconds
        "Timestamp": int(datetime.datetime.now().timestamp()*1000),
        "CloudWatchMetrics": [{
            "Namespace": namespace,
            "Dimensions": [["environment"]],
            "Metrics": [
                {"Name": name} for name in metric_names
            ]
        }]
    }

    print(json.dumps(metrics))