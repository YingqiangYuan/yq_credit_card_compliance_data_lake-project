# -*- coding: utf-8 -*-

"""
Runtime detection — single source of truth for "where is this code running?"

Many parts of this project behave differently depending on whether the code is
executing inside an AWS Lambda function or on a developer's local machine:

- **Config loading** (``one_01_config.py``): on Lambda, config comes from
  Lambda environment variables set at CDK deploy time; locally, it is loaded
  from ``.env`` / ``.env.shared`` files via ``python-dotenv``.
- **Boto session** (``one_02_boto_ses.py``): on Lambda, the default execution
  role credentials are used; locally, a named AWS CLI profile is used.

By wrapping the detection in a singleton ``runtime`` object and importing it
everywhere, we avoid scattering ``os.environ.get("AWS_LAMBDA_FUNCTION_NAME")``
checks throughout the codebase.  Any future runtime-dependent logic should
branch on ``runtime.is_aws_lambda`` rather than inventing its own check.

Usage::

    from .runtime import runtime

    if runtime.is_aws_lambda:
        ...  # Lambda-specific behavior
    else:
        ...  # Local / CI behavior
"""

import which_runtime.api as which_runtime


class Runtime(which_runtime.Runtime):
    """
    Thin subclass of ``which_runtime.Runtime``.

    Kept as a subclass (rather than using the upstream class directly) so that
    project-specific runtime checks can be added later without changing every
    import site.
    """

    pass


runtime = Runtime()
