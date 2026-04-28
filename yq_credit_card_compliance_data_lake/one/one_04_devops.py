# -*- coding: utf-8 -*-

"""
DevOps automation mixin for Lambda deployment and layer management operations.

This module provides comprehensive DevOps automation including containerized Lambda layer building,
source artifact packaging, cross-account permission management, and layer version cleanup.
"""

import typing as T
import shutil
from pathlib import Path

from ..paths import path_enum
from ..lazy_imports import simple_aws_lambda
from ..lazy_imports import aws_lbd_art_builder_uv
from ..lazy_imports import aws_lbd_art_builder_core

if T.TYPE_CHECKING:  # pragma: no cover
    from .one_00_main import One


class OneDevOpsMixin:  # pragma: no cover
    """
    Mixin providing Lambda deployment automation and DevOps operations.
    """

    def _make_layer_builder(self: "One"):
        """
        Create a UvLambdaLayerContainerBuilder configured for this project.
        """
        return aws_lbd_art_builder_uv.layer_api.UvLambdaLayerContainerBuilder(
            path_pyproject_toml=path_enum.path_pyproject_toml,
            py_ver_major=self.config.lbd_func_py_ver_major,
            py_ver_minor=self.config.lbd_func_py_ver_minor,
            is_arm=False,
            skip_prompt=True,
        )

    def build_lambda_layer_only(self: "One"):
        """
        Build Lambda layer in a Docker container (build only — no zip/upload/publish).

        Runs all 4 builder steps:
          1. Preflight check
          2. Prepare environment
          3. Execute build (docker run)
          4. Finalize artifacts (move site-packages → python/)

        The built artifacts are left in ``build/lambda/layer/artifacts/python/``.
        """
        builder = self._make_layer_builder()
        builder.run()

    def build_lambda_layer_in_container(self: "One"):
        """
        Full Lambda layer pipeline: Build → Package (zip) → Upload (S3) → Publish (AWS Lambda).
        """
        builder = self._make_layer_builder()
        workflow = aws_lbd_art_builder_core.layer_api.LayerDeploymentWorkflow(
            builder=builder,
            path_manifest=path_enum.dir_project_root / "uv.lock",
            s3dir_lambda=self.s3dir_lambda,
            layer_name=self.config.lambda_layer_name,
            s3_client=self.s3_client,
            lambda_client=self.lambda_client,
            publish_layer_version_kwargs={
                "CompatibleRuntimes": [
                    f"python{self.config.lbd_func_py_ver_major}.{self.config.lbd_func_py_ver_minor}"
                ],
            },
        )
        layer_deployment = workflow.run()
        print(f"Published layer ARN: {layer_deployment.layer_version_arn}")

    def cleanup_old_layer_versions(self: "One"):
        """
        Clean up old Lambda layer versions keeping only the most recent version.
        """
        deleted_versions = simple_aws_lambda.cleanup_old_layer_versions(
            lambda_client=self.lambda_client,
            layer_name=self.config.lambda_layer_name,
            keep_last_n_versions=1,
            keep_versions_newer_than_seconds=0,
            real_run=True,
        )
        print(f"{deleted_versions = }")

    def build_lambda_source(self: "One"):
        """
        Build Lambda source artifacts using uv and upload the zip to S3.
        """

        result = aws_lbd_art_builder_core.source_api.build_and_upload_source_using_uv(
            s3_client=self.s3_client,
            path_bin_uv=Path(shutil.which("uv")),
            dir_project_root=path_enum.dir_project_root,
            s3dir_source=self.s3dir_lambda.joinpath("source/").to_dir(),
            skip_prompt=True,
        )
        s3uri = result.s3path_source_zip.uri
        print(f"Uploaded source zip: {s3uri}")
        path_enum.path_lambda_source_s3uri.write_text(s3uri)
