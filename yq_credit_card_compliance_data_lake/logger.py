# -*- coding: utf-8 -*-

"""
Project-level logger setup.

A single ``logger`` instance is created here and imported everywhere else.
Using one shared logger (named after the package) means all log output from
this project can be filtered or silenced uniformly — e.g., via the
``disable_logger`` pytest fixture in ``tests/conftest.py``.
"""

from vislog import VisLog

from .paths import PACKAGE_NAME

logger = VisLog(
    name=PACKAGE_NAME,
    log_format="%(message)s",
)
"""
Module-level singleton logger — import this from any module in the package.
"""