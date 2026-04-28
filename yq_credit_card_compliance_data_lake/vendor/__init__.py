# -*- coding: utf-8 -*-

"""
Vendored (copied-in) third-party utilities.

**Why vendor instead of ``pip install``?**  Some utilities are tiny single-file
scripts that don't justify adding a PyPI dependency.  Vendoring them:

- Avoids version conflicts and supply-chain risk for trivial code.
- Keeps the dependency list in ``pyproject.toml`` focused on meaningful
  libraries.
- Locks the exact behavior — no surprise breakage from upstream upgrades.

When vendoring, copy the file as-is and note the upstream source and version
in the module's docstring or a comment at the top of the file.
"""
