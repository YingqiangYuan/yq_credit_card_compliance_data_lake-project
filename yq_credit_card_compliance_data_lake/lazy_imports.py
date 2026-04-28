# -*- coding: utf-8 -*-

"""
Lazy (optional) dependency imports.

**Why lazy?**  The Lambda runtime ships only the core application code and its
production dependencies (installed in a Lambda Layer).  Dev-only tools such as
``simple_aws_lambda``, ``aws_lbd_art_builder_uv``, and ``rstobj`` are **not**
present in the Layer — they are only needed on a developer's local machine for
building, deploying, and generating documentation.

If these packages were imported eagerly at module level, the Lambda handler
would crash on cold start with an ``ImportError``.  By wrapping each import
in a ``try / except`` and falling back to a ``MissingDependency`` sentinel,
the rest of the codebase can import symbols from this module unconditionally.
The sentinel raises a clear, actionable error only when (and if) the symbol is
actually *used* at runtime — which never happens inside Lambda.

**When to add a new entry:**  Any package that is listed under
``[project.optional-dependencies]`` in ``pyproject.toml`` (i.e., not installed
by default) and is imported by non-Lambda code should be added here.
"""

from soft_deps.api import MissingDependency

try:
    import simple_aws_lambda.api as simple_aws_lambda
except ImportError as e:  # pragma: no cover
    simple_aws_lambda = MissingDependency(
        name="simple_aws_lambda",
        error_message=f"please do 'make install-dev'",
    )

try:
    import aws_lbd_art_builder_uv.api as aws_lbd_art_builder_uv
except ImportError as e:  # pragma: no cover
    aws_lbd_art_builder_uv = MissingDependency(
        name="aws_lbd_art_builder_uv",
        error_message=f"please do 'uv sync --extra dev'",
    )

try:
    import aws_lbd_art_builder_core.api as aws_lbd_art_builder_core
except ImportError as e:  # pragma: no cover
    aws_lbd_art_builder_core = MissingDependency(
        name="aws_lbd_art_builder_core",
        error_message=f"please do 'uv sync --extra dev'",
    )

try:
    import rstobj
except ImportError as e:  # pragma: no cover
    rstobj = MissingDependency(
        name="rstobj",
        error_message=f"please do 'make install-dev'",
    )

try:
    import faker
except ImportError as e:  # pragma: no cover
    faker = MissingDependency(
        name="faker",
        error_message=f"please do 'uv sync --extra dev'",
    )
