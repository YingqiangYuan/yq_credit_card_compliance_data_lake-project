.. _Code-Architecture:

Code Architecture
==============================================================================

This document explains how the codebase is organized, how modules depend on
each other, and how to extend the project with new resources.


Directory Structure
------------------------------------------------------------------------------

::

    yq_credit_card_compliance_data_lake-project/
    │
    ├── .env                          # Secret env vars (LOCAL_AWS_PROFILE) — git-ignored
    ├── .env.shared                   # Non-secret env vars — committed to git
    ├── mise.toml                     # Tool versions + task runner definitions
    ├── pyproject.toml                # Python package metadata and dependencies
    │
    ├── yq_credit_card_compliance_data_lake/    # ── Main Python package ──
    │   ├── __init__.py               # Package root
    │   ├── api.py                    # Public API re-exports
    │   ├── _version.py               # Version (from pyproject.toml metadata)
    │   ├── constants.py              # Project-wide constants (LATEST, LIVE, etc.)
    │   ├── paths.py                  # Centralized absolute path references
    │   ├── runtime.py                # Runtime detection (Lambda vs local)
    │   ├── logger.py                 # Shared logger instance
    │   ├── lazy_imports.py           # Dev-only dependency lazy loading
    │   ├── lambda_function.py        # Lambda handler entry point (re-exports)
    │   │
    │   ├── config/                   # Pydantic configuration models
    │   │   ├── config_00_main.py     # Top-level Config class
    │   │   ├── config_01_lbd_func.py # Per-function LbdFunc model
    │   │   ├── config_02_lbd_deploy.py # Deployment mixin (layer name, etc.)
    │   │   └── api.py                # Public re-exports
    │   │
    │   ├── one/                      # Singleton resource access (lazy-loaded)
    │   │   ├── one_00_main.py        # One class (mixin composition)
    │   │   ├── one_01_config.py      # Config loading mixin
    │   │   ├── one_02_boto_ses.py    # Boto session mixin
    │   │   ├── one_03_s3.py          # S3 path mixin
    │   │   ├── one_04_devops.py      # DevOps automation mixin
    │   │   └── api.py                # Public re-exports
    │   │
    │   ├── lbd/                      # Lambda function handlers
    │   │   ├── base.py               # BaseInput / BaseOutput (Pydantic)
    │   │   ├── hello.py              # Simple greeting function
    │   │   └── s3sync.py             # S3 event-driven copy function
    │   │
    │   ├── cdk/                      # CDK infrastructure-as-code
    │   │   ├── stack_enum.py          # Stack registry (lazy entry point)
    │   │   └── stacks/
    │   │       ├── infra_stack.py         # IAM roles, policies
    │   │       ├── infra_stack_exports.py # Type-safe CloudFormation export interface
    │   │       └── lambda_stack.py        # Lambda functions, layers, events
    │   │
    │   ├── tests/                    # Test utilities (inside the package)
    │   │   ├── conftest.py           # Shared pytest fixtures
    │   │   ├── helper.py             # run_unit_test / run_cov_test wrappers
    │   │   └── mock_aws.py           # Mock/real AWS test base class
    │   │
    │   └── vendor/                   # Vendored third-party utilities
    │       └── pytest_cov_helper.py  # Per-module coverage runner
    │
    ├── tests/                        # ── Unit tests (mocked, fast) ──
    │   ├── all.py                    # Run all with full-project coverage
    │   ├── lbd/                      # Lambda handler tests
    │   ├── config/                   # Config model tests
    │   └── cdk/                      # CDK synthesis smoke tests
    │
    ├── tests_int/                    # ── Integration tests (real AWS) ──
    │   ├── lbd/                      # Invoke deployed Lambda functions
    │   └── iac/                      # Verify CloudFormation exports
    │
    └── cdk/                          # ── CDK app entry point ──
        ├── cdk.json                  # CDK configuration
        └── cdk_app.py                # App synthesis script


Module Dependency Graph
------------------------------------------------------------------------------

Modules are organized in layers from most foundational (Layer 0) to
highest-level entry points (Layer 5).  Each layer only depends on layers
below it — **never sideways or upward**.

::

    Layer 5 ─ Entry Points
    │   cdk/cdk_app.py            synthesizes CDK stacks
    │   lambda_function.py        AWS Lambda runtime entry point
    │
    Layer 4 ─ CDK Infrastructure
    │   cdk/stack_enum.py         lazy stack registry
    │   cdk/stacks/infra_stack.py IAM resources
    │   cdk/stacks/lambda_stack.py Lambda + event sources
    │
    Layer 3 ─ Lambda Handlers
    │   lbd/base.py               Pydantic handler base classes
    │   lbd/hello.py              greeting handler
    │   lbd/s3sync.py             S3 copy handler
    │
    Layer 2 ─ Singleton Resource Access
    │   one/one_00_main.py        composed from mixins below
    │   one/one_01_config.py      runtime-aware config loading
    │   one/one_02_boto_ses.py    boto3 session management
    │   one/one_03_s3.py          S3 bucket/path conventions
    │   one/one_04_devops.py      build & deploy automation
    │
    Layer 1 ─ Configuration Models
    │   config/config_00_main.py  top-level Config (Pydantic)
    │   config/config_01_lbd_func.py   per-function LbdFunc model
    │   config/config_02_lbd_deploy.py deployment mixin
    │
    Layer 0 ─ Zero-dependency Foundations
        constants.py              magic strings (LATEST, LIVE, etc.)
        paths.py                  absolute path enumeration
        runtime.py                "am I in Lambda?" detection
        logger.py                 shared logger singleton
        lazy_imports.py           dev-only dependency guard


Key Design Patterns
------------------------------------------------------------------------------

The table below summarizes each pattern, where it lives, and where to find
the **why** explanation in the source code.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Pattern
     - Key Module
     - Why (see module docstring)
   * - Singleton + lazy loading
     - :mod:`yq_credit_card_compliance_data_lake.one`
     - Avoid import-time side effects, prevent circular imports
   * - Mixin composition with numbered files
     - :mod:`yq_credit_card_compliance_data_lake.one.one_00_main`
     - Separation of concerns, explicit dependency order
   * - ``@cached_property`` everywhere
     - :mod:`yq_credit_card_compliance_data_lake.one` (docstring)
     - Compute once on first access; better than ``__init__`` or ``@property``
   * - Runtime-aware config loading
     - :mod:`yq_credit_card_compliance_data_lake.one.one_01_config`
     - Lambda uses env vars from CDK; local uses ``.env`` files
   * - Pydantic Lambda handler (BaseInput/BaseOutput)
     - :mod:`yq_credit_card_compliance_data_lake.lbd.base`
     - Type-safe I/O validation with automatic serialization
   * - ``_config`` back-reference (PrivateAttr)
     - :mod:`yq_credit_card_compliance_data_lake.config.config_01_lbd_func`
     - Child needs parent for computed names; can't be a constructor arg
   * - Infra / Lambda stack separation
     - :mod:`yq_credit_card_compliance_data_lake.cdk.stacks.infra_stack`
     - Different change frequencies, blast-radius isolation
   * - ``StackEnum`` lazy registry
     - :mod:`yq_credit_card_compliance_data_lake.cdk.stack_enum`
     - Only synthesize stacks you access; IDE-friendly
   * - CloudFormation export interface
     - :mod:`yq_credit_card_compliance_data_lake.cdk.stacks.infra_stack_exports`
     - Type-safe, copy-pasteable cross-project resource access
   * - ``AWS_ACCOUNT_ALIAS`` baked at synth time
     - :mod:`yq_credit_card_compliance_data_lake.cdk.stacks.lambda_stack` (line ~88)
     - Avoids IAM API call in Lambda cold start (was causing timeouts)
   * - Lazy dev imports with ``MissingDependency``
     - :mod:`yq_credit_card_compliance_data_lake.lazy_imports`
     - Dev deps not in Lambda Layer; sentinel defers error to point of use
   * - ``api.py`` re-export convention
     - :mod:`yq_credit_card_compliance_data_lake.api`
     - Keep ``__init__.py`` import-free; explicit public surface
   * - Mock/real AWS test switch
     - :mod:`yq_credit_card_compliance_data_lake.tests.mock_aws`
     - One test class, two modes; moto for CI, real AWS for integration
   * - ``if __name__ == "__main__"`` test runner
     - :mod:`yq_credit_card_compliance_data_lake.tests.helper`
     - Run one file with per-module coverage; fast dev feedback
   * - Vendored utilities
     - :mod:`yq_credit_card_compliance_data_lake.vendor`
     - Tiny scripts not worth a PyPI dependency


The ``one`` Singleton — Central Nervous System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :mod:`~yq_credit_card_compliance_data_lake.one` subpackage is the most important
architectural concept.  It provides a single ``one`` instance that lazily
wires together config, AWS sessions, S3 paths, and DevOps operations.

The :class:`~yq_credit_card_compliance_data_lake.one.one_00_main.One` class is composed
from numbered mixin classes:

.. literalinclude:: ../../../../yq_credit_card_compliance_data_lake/one/one_00_main.py
   :language: python
   :pyobject: One
   :caption: one/one_00_main.py — the One class composed from mixins


The Lambda Handler Pattern
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every Lambda function follows the same structure defined in
:class:`~yq_credit_card_compliance_data_lake.lbd.base.BaseInput`:

- A Pydantic ``Input`` model with a ``main()`` method for business logic
- A Pydantic ``Output`` model for the response
- A module-level ``lambda_handler = Input.lambda_handler`` binding

The ``hello`` function is the simplest reference implementation:

.. literalinclude:: ../../../../yq_credit_card_compliance_data_lake/lbd/hello.py
   :language: python
   :caption: lbd/hello.py — reference implementation of a Lambda handler

All handlers are re-exported through a single entry point module.  The CDK
handler path (e.g., ``yq_credit_card_compliance_data_lake.lambda_function.hello_handler``)
always points here:

.. literalinclude:: ../../../../yq_credit_card_compliance_data_lake/lambda_function.py
   :language: python
   :lines: 23-24
   :caption: lambda_function.py — handler registry


How to Extend
------------------------------------------------------------------------------


Adding a New Lambda Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To add a new Lambda function, follow the existing ``hello`` function as a
template.  Each step below shows the reference code to copy and adapt.

**Step 1 — Create the handler module**

Create ``yq_credit_card_compliance_data_lake/lbd/my_func.py``, following the same
pattern as :mod:`~yq_credit_card_compliance_data_lake.lbd.hello`:

.. literalinclude:: ../../../../yq_credit_card_compliance_data_lake/lbd/hello.py
   :language: python
   :caption: Reference: lbd/hello.py — copy this structure for your new function

**Step 2 — Register the handler**

Add an import line to :mod:`~yq_credit_card_compliance_data_lake.lambda_function`,
following the existing pattern:

.. literalinclude:: ../../../../yq_credit_card_compliance_data_lake/lambda_function.py
   :language: python
   :lines: 23-24
   :caption: Reference: lambda_function.py — add a similar line for my_func_handler

**Step 3 — Add environment variables**

Add per-function settings to ``.env.shared``, following the existing entries:

.. literalinclude:: ../../../../.env.shared
   :caption: Reference: .env.shared — add LBD_FUNC_MY_FUNC_* entries in the same pattern
   :lines: 5-8

**Step 4 — Add the config field**

Add a ``lbd_func_my_func`` field to :class:`~yq_credit_card_compliance_data_lake.config.config_00_main.Config`,
next to the existing fields:

.. literalinclude:: ../../../../yq_credit_card_compliance_data_lake/config/config_00_main.py
   :language: python
   :lines: 32-34
   :caption: Reference: config_00_main.py — add lbd_func_my_func in the same pattern

**Step 5 — Load the config**

Add config loading for the new function in the ``else`` branch of
:meth:`~yq_credit_card_compliance_data_lake.one.one_01_config.OneConfigMixin.config`,
following the existing ``lbd_func_hello`` block:

.. literalinclude:: ../../../../yq_credit_card_compliance_data_lake/one/one_01_config.py
   :language: python
   :lines: 39-47
   :caption: Reference: one_01_config.py — copy this block and replace HELLO with MY_FUNC

Then pass it to the ``Config(...)`` constructor and add the ``_config``
back-reference, following these existing lines:

.. literalinclude:: ../../../../yq_credit_card_compliance_data_lake/one/one_01_config.py
   :language: python
   :lines: 58-69
   :caption: Reference: one_01_config.py — add lbd_func_my_func to both places

**Step 6 — CDK auto-discovers**

No CDK changes needed.  The Lambda stack iterates
:attr:`~yq_credit_card_compliance_data_lake.config.config_00_main.Config.lbd_func_mappings`
which auto-discovers all :class:`~yq_credit_card_compliance_data_lake.config.config_01_lbd_func.LbdFunc`
fields on ``Config``.  Only add CDK code if your function needs custom event
sources or extra IAM permissions.

**Step 7 — Write tests**

Create unit and integration tests following the existing examples:

- Unit test — follow ``tests/lbd/test_lbd_hello.py``:

.. literalinclude:: ../../../../tests/lbd/test_lbd_hello.py
   :language: python
   :caption: Reference: tests/lbd/test_lbd_hello.py — simplest handler unit test

- Integration test — follow ``tests_int/lbd/test_lbd_hello.py``:

.. literalinclude:: ../../../../tests_int/lbd/test_lbd_hello.py
   :language: python
   :caption: Reference: tests_int/lbd/test_lbd_hello.py — real Lambda invocation test


Adding a New CDK Stack or Resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Adding a resource to an existing stack:**

Add a new numbered method (e.g., ``s03_create_sqs_queue``) to the
appropriate stack class and call it from ``__init__``.  Follow the section
numbering convention visible in the existing stacks:

.. literalinclude:: ../../../../yq_credit_card_compliance_data_lake/cdk/stacks/infra_stack.py
   :language: python
   :pyobject: InfraStack.__init__
   :caption: Reference: infra_stack.py __init__ — numbered method calls

**Adding an entirely new stack:**

1. Create ``yq_credit_card_compliance_data_lake/cdk/stacks/my_stack.py``.

2. Add a ``@cached_property`` to
   :class:`~yq_credit_card_compliance_data_lake.cdk.stack_enum.StackEnum`, following the
   existing pattern:

   .. literalinclude:: ../../../../yq_credit_card_compliance_data_lake/cdk/stack_enum.py
      :language: python
      :pyobject: StackEnum.lambda_stack
      :caption: Reference: stack_enum.py — copy this pattern for my_stack

3. Access it in ``cdk/cdk_app.py``, following the existing lines:

   .. literalinclude:: ../../../../cdk/cdk_app.py
      :language: python
      :lines: 8-9
      :caption: Reference: cdk_app.py — add ``_ = stack_enum.my_stack``

**Adding a Step Function or other AWS resource:**

Step Functions, SQS queues, DynamoDB tables, etc. follow the same pattern —
create the constructs inside a numbered stack method and wire them up.  For
Step Functions specifically:

1. Define the state machine in a new stack method (e.g.,
   ``s03_create_step_function``) or in a new stack if it's complex.
2. Grant the Lambda execution role permission to invoke the state machine
   (or vice versa) — add a policy statement in
   :meth:`~yq_credit_card_compliance_data_lake.cdk.stacks.infra_stack.InfraStack.s01_create_iam_roles`.
3. If the Step Function needs to invoke Lambda functions, use
   :attr:`~yq_credit_card_compliance_data_lake.config.config_00_main.Config.lbd_func_mappings`
   to get function names dynamically.

**Exporting resources for other projects:**

If other projects need to reference your new resource, add a ``CfnOutput``
in the stack and a corresponding ``@cached_property`` in
:mod:`~yq_credit_card_compliance_data_lake.cdk.stacks.infra_stack_exports`.  See that
module's docstring for the full extension guide.
