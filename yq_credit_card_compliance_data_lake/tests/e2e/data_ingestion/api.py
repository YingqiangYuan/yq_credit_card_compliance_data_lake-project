# -*- coding: utf-8 -*-

"""
Public API for the data-ingestion e2e helpers.
"""

from .producer import produce
from .consumer import consume
from ._kinesis import purge_stream
from ._kinesis import get_test_stream_name
