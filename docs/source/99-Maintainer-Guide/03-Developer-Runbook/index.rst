.. _Developer-Runbook:

Developer Runbook
==============================================================================

This is the hands-on operations guide.  For each common task, it lists exactly
which files to touch, which commands to run, and in what order.


First-Time Setup
------------------------------------------------------------------------------

1. **Install mise** (if not already installed):

   .. code-block:: bash

       curl https://mise.run | sh

2. **Clone and enter the project:**

   .. code-block:: bash

       git clone <repo-url>
       cd yq_credit_card_compliance_data_lake-project

3. **Install all tools and dependencies:**

   .. code-block:: bash

       mise install   # installs Python 3.12, uv, node, aws-cdk, etc.
       mise run inst   # creates .venv and installs all Python deps

4. **Configure environment variables:**

   Non-secret settings are committed in ``.env.shared`` — no action needed:

   .. literalinclude:: ../../../../.env.shared
      :caption: .env.shared — shared, non-secret configuration

   Secrets go in ``.env`` (git-ignored).  Create it with your AWS CLI
   profile name:

   .. code-block:: bash

       echo 'LOCAL_AWS_PROFILE="your-aws-profile-name"' > .env

   ``LOCAL_AWS_PROFILE`` is the only secret needed.  It tells boto3 which
   named profile to use for local development and deployment.

5. **Verify AWS credentials:**

   .. code-block:: bash

       aws sts get-caller-identity --profile your-aws-profile-name


Environment Variables — ``.env`` vs ``.env.shared``
------------------------------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - File
     - Purpose
     - Git Status
   * - ``.env.shared``
     - Project config, Lambda function settings, layer version
     - **Committed** — shared across the team
   * - ``.env``
     - Sensitive values (``LOCAL_AWS_PROFILE``)
     - **Git-ignored** — each developer creates their own

Both files are loaded by ``python-dotenv`` at config init time (see
:mod:`~yq_credit_card_compliance_data_lake.one.one_01_config`).  On Lambda,
environment variables are set at CDK deploy time instead.


Mise Task Reference — Lambda & CDK
------------------------------------------------------------------------------

These are the tasks most relevant to Lambda deployment.  Run any task with
``mise run <task-name>``.

.. literalinclude:: ../../../../mise.toml
   :language: toml
   :lines: 118-163
   :caption: mise.toml — CDK and Lambda DevOps tasks


Day-to-Day Workflows
------------------------------------------------------------------------------


Scenario 1: Changed Business Logic (Lambda source code)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You edited files in :mod:`~yq_credit_card_compliance_data_lake.lbd` or other package
modules — but did **not** change ``pyproject.toml`` dependencies.

**What happens:** ``mise run cdk-up`` automatically runs
``lambda-source-deploy`` first (it is declared as a dependency in
``mise.toml``), which builds a source zip and uploads it to S3.  Then CDK
deploys the new code.

.. code-block:: bash

    # 1. Run unit tests
    mise run cov

    # 2. Deploy (source zip is built automatically)
    mise run cdk-up

    # 3. Run integration tests
    pytest tests_int/ -s --tb=native

**Files you touched:**

- ``yq_credit_card_compliance_data_lake/lbd/*.py`` (or any package source code)

**Files you did NOT need to touch:**

- ``.env.shared`` — no config change
- ``mise.toml`` — no task change
- ``pyproject.toml`` — no dependency change


Scenario 2: Changed Python Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You added, removed, or upgraded a dependency in ``pyproject.toml``.  The
Lambda Layer must be rebuilt because it ships the installed packages.

.. code-block:: bash

    # 1. Sync local venv
    mise run inst

    # 2. (Optional) Build layer locally to verify it works
    mise run lambda-layer-build-only

    # 3. Full layer pipeline: Build → Zip → Upload S3 → Publish Lambda Layer
    mise run lambda-layer-deploy

    # 4. Update the layer version number in .env.shared
    #    (the new version is printed by lambda-layer-deploy)
    #    Edit: LBD_FUNC_LAYER_VERSION="3"  (was "2")

    # 5. Deploy CDK (picks up new layer version + new source code)
    mise run cdk-up

**Files you touched:**

- ``pyproject.toml`` — dependency change
- ``.env.shared`` — bump ``LBD_FUNC_LAYER_VERSION``

**Key distinction:** ``lambda-layer-build-only`` builds the layer in Docker
but does **not** zip, upload, or publish it.  Use it for local verification.
``lambda-layer-deploy`` does the full pipeline.


Scenario 3: Changed IAM Permissions or Infrastructure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You edited :mod:`~yq_credit_card_compliance_data_lake.cdk.stacks.infra_stack` to add
or modify IAM roles, policies, or other long-lived resources.

.. code-block:: bash

    # 1. Preview changes
    cd cdk && cdk diff --all --profile $LOCAL_AWS_PROFILE && cd ..

    # 2. Deploy
    mise run cdk-up

**Files you touched:**

- ``yq_credit_card_compliance_data_lake/cdk/stacks/infra_stack.py``

If you added a new ``CfnOutput``, also update
``yq_credit_card_compliance_data_lake/cdk/stacks/infra_stack_exports.py`` with a
matching ``@cached_property``.


Scenario 4: Adding a New Lambda Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See the step-by-step guide in the **Code Architecture** document
(``02-Code-Architect``).  Summary of files to create or modify:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - File
     - Action
   * - ``yq_credit_card_compliance_data_lake/lbd/my_func.py``
     - **Create** — handler module (Input/Output/main)
   * - ``yq_credit_card_compliance_data_lake/lambda_function.py``
     - **Edit** — add ``from ... import lambda_handler as my_func_handler``
   * - ``.env.shared``
     - **Edit** — add ``LBD_FUNC_MY_FUNC_*`` env vars
   * - ``yq_credit_card_compliance_data_lake/config/config_00_main.py``
     - **Edit** — add ``lbd_func_my_func`` field
   * - ``yq_credit_card_compliance_data_lake/one/one_01_config.py``
     - **Edit** — load new ``LbdFunc`` from env vars
   * - ``tests/lbd/test_lbd_my_func.py``
     - **Create** — unit test
   * - ``tests_int/lbd/test_lbd_my_func.py``
     - **Create** — integration test

Then deploy:

.. code-block:: bash

    mise run cov        # verify unit tests pass
    mise run cdk-up     # deploy
    pytest tests_int/lbd/test_lbd_my_func.py -s  # verify in AWS


Scenario 5: Adding New CDK Resources (non-Lambda)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For new resources like SQS queues, DynamoDB tables, or Step Functions:

1. Add constructs to an existing stack (e.g., ``infra_stack.py``) using a new
   numbered method, or create a new stack file and register it in
   :mod:`~yq_credit_card_compliance_data_lake.cdk.stack_enum`.

2. If the Lambda function needs permission to access the new resource, add an
   IAM policy statement in ``infra_stack.py``.

3. Deploy:

   .. code-block:: bash

       mise run cdk-up


Scenario 6: Updating Lambda Function Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To change timeout, memory, or other per-function settings, edit
``.env.shared``:

.. code-block:: bash

    # Example: increase s3sync timeout from 10 to 30 seconds
    LBD_FUNC_S3_SYNC_TIMEOUT="30"

Then deploy:

.. code-block:: bash

    mise run cdk-up


Running Tests
------------------------------------------------------------------------------


Unit Tests (mocked, no AWS credentials needed)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # All unit tests with coverage
    mise run cov

    # Single test file with per-module coverage
    python tests/lbd/test_lbd_hello.py

    # CDK synthesis smoke test (no coverage — tests CDK internals)
    mise run test

    # Single test subfolder
    python tests/lbd/all.py


Integration Tests (real AWS, requires deployment)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # All integration tests
    pytest tests_int/ -s --tb=native

    # Single integration test
    pytest tests_int/lbd/test_lbd_hello.py -s --tb=native

    # All Lambda integration tests
    python tests_int/lbd/all.py

Integration tests require:

- Valid AWS credentials (``LOCAL_AWS_PROFILE`` in ``.env``)
- A prior ``mise run cdk-up`` deployment


Teardown and Cleanup
------------------------------------------------------------------------------

.. code-block:: bash

    # Destroy all CDK stacks (with confirmation prompt)
    mise run cdk-down-ask

    # Destroy all CDK stacks (force, no prompt)
    mise run cdk-down

    # Clean up old Lambda layer versions (keeps latest 1)
    mise run lambda-layer-cleanup


Troubleshooting
------------------------------------------------------------------------------

**CDK deploy fails with "Export ... cannot be deleted":**
The Lambda stack imports the IAM role ARN from the infra stack.  You cannot
delete the infra stack while the Lambda stack exists.  Destroy Lambda first:
``cd cdk && cdk destroy yq-credit-card-compliance-data-lake-lbd --profile $LOCAL_AWS_PROFILE``.

**Lambda cold start hangs:**
Check that ``AWS_ACCOUNT_ALIAS`` is set in the Lambda environment variables
(visible in the AWS console).  If missing, redeploy with ``mise run cdk-up``.
See :mod:`~yq_credit_card_compliance_data_lake.cdk.stacks.lambda_stack` line ~88 for
the explanation.

**``ImportError`` when running tests locally:**
Run ``mise run inst`` to ensure all dev dependencies are installed.

**``lambda-layer-build-only`` fails:**
This task builds the layer in a Docker container.  Make sure Docker is
running.  Check the Docker daemon with ``docker info``.

**Layer version mismatch after deploy:**
After ``mise run lambda-layer-deploy``, update ``LBD_FUNC_LAYER_VERSION`` in
``.env.shared`` to the new version number printed by the command, then
redeploy with ``mise run cdk-up``.
