# -*- coding: utf-8 -*-

"""
Root-level pytest configuration.

Re-exports all fixtures from the package's internal ``tests/conftest.py`` so
that they are available to every test file under ``tests/`` without explicit
imports.  Pytest automatically loads ``conftest.py`` at each directory level.

**Why re-export from the package?**  Fixtures like ``disable_logger`` are
defined inside ``yq_credit_card_compliance_data_lake/tests/conftest.py`` (the package's
test utilities).  By star-importing them here, they become available to the
top-level ``tests/`` directory — the actual test suite — without duplicating
fixture code.
"""

from yq_credit_card_compliance_data_lake.tests.conftest import *
