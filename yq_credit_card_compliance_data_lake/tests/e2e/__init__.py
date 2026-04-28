# -*- coding: utf-8 -*-

"""
End-to-end smoke helpers — packaged-side counterpart to the project-root
``tests_e2e/`` directory.

**Why is the actual logic inside the package?**  Keeping the producer /
consumer / purge functions here (instead of inside ad-hoc scripts) lets the
top-level ``tests_e2e/`` runners stay extremely thin (import + call), allows
them to share helpers via normal Python imports, and makes the same code
unit-testable should we want to in the future.
"""
