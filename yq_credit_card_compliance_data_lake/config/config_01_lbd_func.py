# -*- coding: utf-8 -*-

"""
Lambda function configuration model.

Each Lambda function in this project is represented by a ``LbdFunc`` instance
that holds its deployment parameters (timeout, memory, layers, etc.) and
provides computed naming variants (snake_case, slug, CamelCase) used by CDK
constructs and CloudFormation logical IDs.

**``_config`` back-reference — why a ``PrivateAttr``?**

A ``LbdFunc`` needs access to its parent ``Config`` to compute derived values
like the full function name (``{project_name_snake}-{short_name}``).  But
Pydantic models are validated at construction time, and the parent ``Config``
is still being built when its child ``LbdFunc`` fields are validated — so the
back-reference cannot be a constructor argument.

Instead, ``_config`` is declared as a ``PrivateAttr`` (excluded from Pydantic
validation) and assigned *after* construction in ``one_01_config.py``::

    config.lbd_func_hello._config = config

This is only needed locally (not on Lambda), because on Lambda the ``LbdFunc``
objects are ``None`` — the Lambda handler doesn't need deployment metadata.
"""

import typing as T
from pydantic import BaseModel, Field, PrivateAttr
from boltons.strutils import slugify, under2camel

from ..constants import LATEST

if T.TYPE_CHECKING:  # pragma: no cover
    from .config_00_main import Config


class LbdFunc(BaseModel):
    """
    Represent a lambda function.
    """

    short_name: str = Field()
    handler: str = Field()
    timeout: int = Field()
    memory: int = Field()
    iam_role: str | None = Field(default=None)
    env_vars: dict[str, str] = Field(default_factory=dict)
    layers: list[str] = Field(default_factory=list)
    subnet_ids: list[str] | None = Field(default_factory=list)
    security_group_ids: list[str] | None = Field(default_factory=list)
    reserved_concurrency: int | None = Field(default=None)
    live_version1: str | None = Field(default=None)
    live_version2: str | None = Field(default=None)
    live_version2_percentage: float | None = Field(default=None)

    _config: "Config" = PrivateAttr()

    @property
    def config(self) -> "Config":
        """
        The config this lambda function belongs to.
        """
        return self._config

    @property
    def name(self) -> str:
        """
        Full name of the Lambda function.
        """
        return f"{self.config.project_name_snake}-{self.short_name}"

    @property
    def short_name_slug(self) -> str:
        """
        Example: ``my-func``
        """
        return slugify(self.short_name, delim="-")

    @property
    def short_name_snake(self) -> str:
        """
        Example: ``my_func``
        """
        return slugify(self.short_name, delim="_")

    @property
    def short_name_camel(self) -> str:
        """
        The lambda function short name in camel case. This is usually used
        in CloudFormation logic ID.

        Example: ``MyFunc``
        """
        return under2camel(slugify(self.short_name, delim="_"))
