# -*- coding: utf-8 -*-

"""
S3 path management mixin — convention-driven bucket and prefix layout.

**Why a mixin with ``cached_property``?**  S3 bucket names and key prefixes
are derived from the AWS account alias, region, and project name.  Computing
them requires a boto call (for the account alias), so we cache the result.
Putting them in a mixin keeps S3 concerns separate from boto-session concerns
(``one_02_boto_ses.py``) and config concerns (``one_01_config.py``).

**Bucket naming convention:**

- ``{account_alias}-{region}-data`` — project runtime data (input / output
  files that Lambda functions read and write).
- ``{account_alias}-{region}-artifacts`` — build artifacts (Lambda source
  zips, layer zips, deployment manifests).

Each bucket has a per-project prefix: ``projects/{project_name}/``.

This convention is intentionally simple: one data bucket and one artifacts
bucket per account-region pair, with project isolation via S3 key prefixes.
"""

import typing as T
from functools import cached_property

from s3pathlib import S3Path

from .._version import __version__

if T.TYPE_CHECKING:  # pragma: no cover
    from .one_00_main import One


class OneS3Mixin:  # pragma: no cover
    """
    Mixin providing lazy-loaded S3 bucket names and path objects.

    All properties follow the naming pattern ``s3bucket_*`` for bucket name
    strings and ``s3dir_*`` / ``s3path_*`` for ``S3Path`` objects.
    """

    @cached_property
    def s3bucket_data(self: "One") -> str:
        """S3 bucket for project runtime data (inputs, outputs, etc.)."""
        return f"{self.aws_account_alias}-{self.aws_region}-data"

    @cached_property
    def s3bucket_artifacts(self: "One") -> str:
        """S3 bucket for build and deployment artifacts (source zips, layers)."""
        return f"{self.aws_account_alias}-{self.aws_region}-artifacts"

    @cached_property
    def s3dir_data(self: "One") -> S3Path:
        """Root S3 directory for this project's runtime data."""
        return S3Path(
            f"s3://{self.s3bucket_data}/projects/{self.config.project_name}/"
        ).to_dir()

    @cached_property
    def s3dir_artifacts(self: "One") -> S3Path:
        """Root S3 directory for this project's build artifacts."""
        return S3Path(
            f"s3://{self.s3bucket_artifacts}/projects/{self.config.project_name}/"
        ).to_dir()

    @property
    def s3dir_lambda(self: "One") -> "S3Path":
        """
        Where you store lambda related artifacts.

        example: ``${s3dir_artifacts}/lambda/``
        """
        return self.s3dir_artifacts.joinpath("lambda").to_dir()

    @property
    def s3path_lambda_source_zip(self: "One") -> "S3Path":
        """
        Where you store lambda source zip artifact.

        example: ``${s3dir_lambda}/source/${version}/source.zip``
        """
        import aws_lambda_artifact_builder.api as aws_lambda_artifact_builder

        layout = aws_lambda_artifact_builder.SourceS3Layout(
            s3dir_lambda=self.s3dir_lambda,
        )
        s3path = layout.get_s3path_source_zip(source_version=__version__)
        return s3path

    @property
    def s3dir_source(self: "One") -> S3Path:
        """S3 directory used as the *source* location for the s3sync Lambda function."""
        return self.s3dir_data.joinpath("source").to_dir()

    @property
    def s3dir_target(self: "One") -> S3Path:
        """S3 directory used as the *target* location for the s3sync Lambda function."""
        return self.s3dir_data.joinpath("target").to_dir()
