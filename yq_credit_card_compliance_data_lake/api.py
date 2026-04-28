# -*- coding: utf-8 -*-

"""
Public API re-export module.

**Why an ``api.py`` instead of putting exports in ``__init__.py``?**

Separating the public API into its own module avoids import-time side effects
in ``__init__.py``.  When Python processes the ``__init__.py`` of a package it
executes *everything* in the file — including any heavy imports.  Keeping
``__init__.py`` minimal (or empty) means that importing the package itself is
cheap; consumers explicitly opt in to the full API surface by writing
``from yq_credit_card_compliance_data_lake.api import one``.

This same ``api.py`` convention is used at every subpackage level (``config/``,
``one/``) so that internal refactoring never accidentally breaks the public
contract.
"""

from .one.api import one
