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

    # --------------------------------------------------------------------------
    # Data-lake medallion layout
    #
    # Layer-level directories (bronze/silver/gold/quarantine) follow the standard
    # medallion architecture; ``landing`` and ``manifest`` are batch-pipeline
    # staging areas described in doc1 §2.
    #
    # Source-specific subdirectories (e.g., ``s3dir_bronze_transactions``) are
    # added per phase as each ingestion source is implemented — Phase 2 covers
    # only Transaction; FraudAlert / batch sources land in later phases.
    # --------------------------------------------------------------------------
    @cached_property
    def s3dir_bronze(self: "One") -> S3Path:
        """Bronze layer — raw, immutable records as ingested. ``${s3dir_data}/bronze/``."""
        return self.s3dir_data.joinpath("bronze").to_dir()

    @cached_property
    def s3dir_silver(self: "One") -> S3Path:
        """Silver layer — cleaned, conformed, deduplicated. ``${s3dir_data}/silver/``."""
        return self.s3dir_data.joinpath("silver").to_dir()

    @cached_property
    def s3dir_gold(self: "One") -> S3Path:
        """Gold layer — aggregated, business-ready datasets. ``${s3dir_data}/gold/``."""
        return self.s3dir_data.joinpath("gold").to_dir()

    @cached_property
    def s3dir_quarantine(self: "One") -> S3Path:
        """Quarantine — records that failed ERROR-level data-quality checks.

        Mirrored per source under here (e.g. ``quarantine/transactions/``) so
        each ingestion path can drop bad records into its own subfolder.
        """
        return self.s3dir_data.joinpath("quarantine").to_dir()

    @cached_property
    def s3dir_landing(self: "One") -> S3Path:
        """Landing zone for batch sources — files awaiting validation/ETL. See doc1 §2."""
        return self.s3dir_data.joinpath("landing").to_dir()

    @cached_property
    def s3dir_manifest(self: "One") -> S3Path:
        """Per-batch manifest files (checksum, expected row count, schema version)."""
        return self.s3dir_data.joinpath("manifest").to_dir()

    # --- Per-source subdirectories — Phase 2 (Transaction only) ---
    @cached_property
    def s3dir_bronze_transactions(self: "One") -> S3Path:
        """Bronze for Kinesis transaction firehose. ``${s3dir_bronze}/transactions/``.

        Records are partitioned underneath by ``year=/month=/day=/hour=`` —
        partitioning is added by the consumer Lambda (Phase 4), not here.
        """
        return self.s3dir_bronze.joinpath("transactions").to_dir()

    @cached_property
    def s3dir_quarantine_transactions(self: "One") -> S3Path:
        """Quarantine for transaction records that failed ERROR-level checks."""
        return self.s3dir_quarantine.joinpath("transactions").to_dir()
