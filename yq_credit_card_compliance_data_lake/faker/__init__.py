# -*- coding: utf-8 -*-

"""
Generic faker utilities — business-agnostic helpers that the third-party
``Faker`` library does not provide.

Anything domain-specific (transaction shapes, MCC pools, fraud-alert
distributions) lives in the corresponding ``data_ingestion`` business module
instead. The rule of thumb: if swapping the project to a different vertical
(e.g., healthcare claims) would require rewriting the helper, it is **not**
generic and does not belong here.
"""
