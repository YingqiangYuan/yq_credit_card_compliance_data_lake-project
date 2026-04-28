# -*- coding: utf-8 -*-

"""
Public API for the ``data_ingestion`` subpackage.
"""

from .models import Transaction
from .faker import TransactionFaker
from .producer.api import send_records
from .producer.api import SendResult
from .consumer.api import Consumer
from .consumer.api import drain_shard
from .consumer.api import iter_shard_ids
from .consumer.api import decode_kinesis_records
from .quality.api import ValidationResult
from .quality.api import validate_transaction
from .writer.api import build_partition_path
from .writer.api import write_ndjson_to_s3
from .dynamodb_table import PipelineMetadata
