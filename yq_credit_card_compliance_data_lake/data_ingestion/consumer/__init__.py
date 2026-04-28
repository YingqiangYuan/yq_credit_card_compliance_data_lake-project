# -*- coding: utf-8 -*-

"""
Consumer subpackage — sync readers that pull records from streaming sources
(Kinesis in Phase 1, Kafka in a later phase).

A consumer is **only** responsible for "how to read": shard discovery,
``GetShardIterator`` / ``GetRecords`` plumbing, polling cadence. It does
**not** decode payloads, validate records, or write to the lake — those
concerns live in the Lambda handler that wraps the consumer (Phase 4).
"""
