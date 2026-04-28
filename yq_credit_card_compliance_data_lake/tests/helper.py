# -*- coding: utf-8 -*-

"""
Project-specific test runner wrappers.

**Why these wrappers?**  The vendored ``pytest_cov_helper`` requires explicit
``root_dir`` and ``htmlcov_dir`` arguments.  These wrappers pre-fill them from
``path_enum`` so that every test file's ``if __name__ == "__main__"`` block
stays concise — just pass ``__file__`` and the module name.

**The ``if __name__ == "__main__"`` pattern — why?**

Every test file in this project ends with::

    if __name__ == "__main__":
        from yq_credit_card_compliance_data_lake.tests import run_cov_test
        run_cov_test(__file__, "yq_credit_card_compliance_data_lake.some_module")

This lets you run a single test file directly (``python tests/test_foo.py``)
and immediately see per-module coverage in your terminal and browser — without
configuring pytest CLI flags or ``.ini`` files.  During development this is
much faster than running the full test suite, and it encourages writing tests
alongside the code they cover.
"""

from ..paths import path_enum
from ..vendor.pytest_cov_helper import (
    run_unit_test as _run_unit_test,
    run_cov_test as _run_cov_test,
)


def run_unit_test(
    script: str,
    is_folder: bool = False,
):
    _run_unit_test(
        script=script,
        root_dir=f"{path_enum.dir_project_root}",
        is_folder=is_folder,
    )


def run_cov_test(
    script: str,
    module: str,
    preview: bool = False,
    is_folder: bool = False,
):
    _run_cov_test(
        script=script,
        module=module,
        root_dir=f"{path_enum.dir_project_root}",
        htmlcov_dir=f"{path_enum.dir_htmlcov}",
        preview=preview,
        is_folder=is_folder,
    )
