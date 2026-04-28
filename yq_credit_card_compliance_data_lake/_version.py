# -*- coding: utf-8 -*-

"""
Single source of truth for the package version.

The version string is read from the installed package metadata at import time
(populated by ``pyproject.toml``'s ``[project] version`` field).  This means
there is only one place to bump the version — ``pyproject.toml`` — and every
other part of the codebase (Sphinx docs, CDK tags, S3 artifact paths) picks it
up automatically via ``from ._version import __version__``.
"""

from importlib.metadata import version

from yq_credit_card_compliance_data_lake.paths import PACKAGE_NAME

__version__ = version(PACKAGE_NAME)