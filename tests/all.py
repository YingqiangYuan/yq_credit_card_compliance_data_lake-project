# -*- coding: utf-8 -*-

"""
Run **all** unit tests with full-project coverage.

This script is the top-level test aggregator.  Running ``python tests/all.py``
discovers every test under ``tests/`` and measures coverage for the entire
``yq_credit_card_compliance_data_lake`` package.  It produces both a terminal summary
and an HTML report in ``htmlcov/``.

**Why a separate ``all.py`` file?**  The ``if __name__ == "__main__"`` pattern
(see ``tests/helper.py`` for the rationale) needs a script to anchor the "run
everything" use case.  ``pytest`` alone doesn't set the ``--cov`` scope for
you, and configuring it in ``pyproject.toml`` couples the scope to one fixed
module — this script lets you run full or per-module coverage with the same
pattern.
"""

if __name__ == "__main__":
    from yq_credit_card_compliance_data_lake.tests import run_cov_test

    run_cov_test(
        __file__,
        "yq_credit_card_compliance_data_lake",
        is_folder=True,
        preview=False,
    )
