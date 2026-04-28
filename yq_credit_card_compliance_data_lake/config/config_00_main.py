# -*- coding: utf-8 -*-

"""
Top-level project configuration model.

``Config`` aggregates all settings needed for CDK deployment and local
development: project naming, AWS region, Python version, and per-function
Lambda configurations.  It inherits from ``LbdFuncDeployMixin`` for
deployment-specific computed properties (e.g., ``lambda_layer_name``).

Properties like ``project_name_snake``, ``project_name_slug``, and
``cloudformation_stack_name`` derive naming variants from a single
``project_name`` source of truth — change it once, and every CloudFormation
resource name, S3 prefix, and IAM role name updates consistently.
"""

from pydantic import BaseModel
from pydantic import Field

from .config_01_lbd_func import LbdFunc
from .config_02_lbd_deploy import LbdFuncDeployMixin


class Config(
    BaseModel,
    LbdFuncDeployMixin,
):
    project_name: str = Field()
    aws_region: str = Field()
    local_aws_profile: str | None = Field(default=None)

    lbd_func_py_ver: str | None = Field(default=None)
    lbd_func_hello: LbdFunc | None = Field()
    lbd_func_s3sync: LbdFunc | None = Field()

    @property
    def project_name_snake(self) -> str:
        return self.project_name.replace("-", "_")

    @property
    def project_name_slug(self) -> str:
        return self.project_name_snake.replace("_", "-")

    @property
    def cloudformation_stack_name(self) -> str:
        return self.project_name_slug

    @property
    def cloudformation_stack_url(self) -> str:
        return (
            f"https://{self.aws_region}.console.aws.amazon.com"
            f"/cloudformation/home?region={self.aws_region}#"
            f"/stacks?filteringText={self.cloudformation_stack_name}&filteringStatus=active&viewNested=true"
        )

    @property
    def lbd_func_py_ver_major(self) -> int:
        return int(self.lbd_func_py_ver.split(".")[0])

    @property
    def lbd_func_py_ver_minor(self) -> int:
        return int(self.lbd_func_py_ver.split(".")[1])

    @property
    def lbd_func_mappings(self) -> dict[str, LbdFunc]:
        result = {}
        for k in self.__class__.model_fields:
            v = getattr(self, k)
            if isinstance(v, LbdFunc):
                result[v.short_name] = v
        return result

    @property
    def lbd_func_env_vars(self) -> dict[str, str]:
        return {
            "PROJECT_NAME": self.project_name,
        }
