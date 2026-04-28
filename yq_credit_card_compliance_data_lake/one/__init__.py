# -*- coding: utf-8 -*-

"""
Singleton Variable Access Subpackage (``one``)

**What:** A single ``one = One()`` instance that provides lazy-loaded access to
every shared resource the project needs — configuration, AWS sessions, S3 paths,
and DevOps automation.

**Why a singleton?**  In a Lambda function (and in local scripts), many
resources are expensive to create (boto sessions, config parsing) and should be
created at most once per process.  A module-level singleton with
``@cached_property`` attributes gives us:

- **Lazy initialization** — nothing is created until first use.  Importing
  ``from .one.api import one`` is free; the boto session is only built when
  ``one.boto_ses`` is first accessed.
- **No circular imports** — because initialization is deferred, the import
  graph stays acyclic even though config, boto, S3, and DevOps code all
  cross-reference each other.
- **Single source of truth** — every call site shares the same config and
  session instance, avoiding subtle bugs from duplicated state.

**Why ``@cached_property`` instead of ``__init__`` or plain ``@property``?**

This pattern is used throughout the project (``one/``, ``config/``, ``cdk/``):

- vs ``__init__``: Eager initialization in ``__init__`` would force every
  resource to be created at import time — even resources the current code path
  never uses.  In Lambda, this wastes cold-start time; locally, it can fail if
  some credentials or env vars are not set for an unrelated service.
- vs ``@property``: A plain property re-evaluates on every access.  For
  expensive operations (STS calls, config parsing, boto sessions) this is
  wasteful and can produce inconsistent results if the underlying state
  changes mid-process.
- ``@cached_property`` computes the value **once, on first access**, then
  caches it for the lifetime of the instance — the best of both worlds.

**File organization:** The ``One`` class is assembled from numbered mixin files
(``one_00_main.py``, ``one_01_config.py``, …).  See ``one_00_main.py`` module
docstring for why the mixin pattern and numbered naming convention are used.

**Usage**::

    from yq_credit_card_compliance_data_lake.one.api import one

    one.config          # lazy-loaded Config object
    one.boto_ses        # lazy-loaded boto3.Session
    one.s3dir_lambda    # lazy-loaded S3Path
"""
