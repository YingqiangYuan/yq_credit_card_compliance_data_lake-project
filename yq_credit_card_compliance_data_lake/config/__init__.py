# -*- coding: utf-8 -*-

"""
Configuration subpackage — Pydantic data models for project and Lambda settings.

Files are numbered (``config_00_``, ``config_01_``, ``config_02_``) to indicate
dependency order: ``config_00_main`` imports from ``config_01_lbd_func`` and
``config_02_lbd_deploy``, never the other way around.  See
``one/one_00_main.py`` module docstring for the rationale behind this naming
convention.

Public symbols are re-exported through ``config/api.py``.
"""
