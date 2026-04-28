# -*- coding: utf-8 -*-

"""
Core singleton class combining all mixin functionality for centralized resource access.

**Why the mixin composition pattern?**

The ``One`` class is assembled from multiple mixin classes rather than being
defined monolithically in a single file.  This design is intentional:

1. **Separation of concerns** — each mixin owns exactly one responsibility
   (config, boto sessions, S3 paths, DevOps automation).  A developer looking
   for "how do we resolve S3 paths?" goes straight to ``one_03_s3.py`` without
   wading through unrelated boto-session or deployment code.

2. **Independent evolution** — mixins can be added, removed, or reordered
   without touching unrelated code.  For example, adding a new
   ``one_05_monitoring.py`` mixin only requires creating the file and listing
   it in the ``One`` class bases below.

3. **Numbered file naming convention** — files are prefixed ``one_00_``,
   ``one_01_``, … to make the **reading order** and **dependency order**
   explicit.  Lower-numbered mixins are more foundational (e.g., config must
   exist before boto session, boto session before S3 paths).  The same
   convention is used in ``config/`` (``config_00_``, ``config_01_``, …) and
   CDK stack methods (``s01_``, ``s02_``, …).

4. **Kept in one class (not separate objects)** — all mixins share ``self``, so
   a property in ``OneS3Mixin`` can naturally access ``self.boto_ses`` defined
   in ``OneBotoSesMixin``.  No wiring, no dependency injection — just attribute
   access on a single instance.
"""

try:
    from pywf_internal_proprietary.api import PyWf
except ImportError:  # pragma: no cover
    pass
from ..runtime import runtime

from .one_01_config import OneConfigMixin
from .one_02_boto_ses import OneBotoSesMixin
from .one_03_s3 import OneS3Mixin
from .one_04_devops import OneDevOpsMixin


class One(
    OneConfigMixin,
    OneBotoSesMixin,
    OneS3Mixin,
    OneDevOpsMixin,
):  # pragma: no cover
    """
    Main singleton class providing unified access to all application resources and services.
    """

    runtime = runtime


one = One()
