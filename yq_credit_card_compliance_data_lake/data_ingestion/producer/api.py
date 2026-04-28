# -*- coding: utf-8 -*-

"""
Public API for the producer subpackage.
"""

from .producer_00_base import SendResult
from .producer_00_base import to_kinesis_record
from .producer_00_base import chunk
from .producer_01_kinesis import send_records
