# -*- coding: utf-8 -*-

from soft_deps.api import MissingDependency

try:
    import simple_aws_lambda.api as simple_aws_lambda
except ImportError as e:  # pragma: no cover
    simple_aws_lambda = MissingDependency(
        name="simple_aws_lambda",
        error_message=f"please do 'make install-dev'",
    )

try:
    import aws_lambda_artifact_builder.api as aws_lambda_artifact_builder
except ImportError as e:  # pragma: no cover
    aws_lambda_artifact_builder = MissingDependency(
        name="aws_lambda_artifact_builder",
        error_message=f"please do 'make install-dev'",
    )

try:
    import rstobj
except ImportError as e:  # pragma: no cover
    rstobj = MissingDependency(
        name="rstobj",
        error_message=f"please do 'make install-dev'",
    )
