# -*- coding: utf-8 -*-

"""
Producer subpackage — sync writers that push records to streaming /
object-store targets (Kinesis in Phase 1, Kafka and S3 Landing Zone in later
phases).

A producer is **only** responsible for "how to deliver": batching, serializing,
calling the SDK, collecting failures. It is not responsible for generating
data, validating data, or implementing business rules — those concerns live in
sibling modules (``faker.py``, ``consumer/``, ``quality/``).
"""
