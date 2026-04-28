# -*- coding: utf-8 -*-

"""
Test utilities subpackage.

Re-exports ``run_unit_test`` and ``run_cov_test`` so that every test file can
use the ``if __name__ == "__main__"`` single-file runner pattern with a short
import::

    if __name__ == "__main__":
        from yq_credit_card_compliance_data_lake.tests import run_cov_test

        run_cov_test(__file__, "yq_credit_card_compliance_data_lake.some_module")
"""

from .helper import run_unit_test, run_cov_test
