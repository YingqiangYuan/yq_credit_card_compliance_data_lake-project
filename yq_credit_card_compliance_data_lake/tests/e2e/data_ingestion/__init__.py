# -*- coding: utf-8 -*-

"""
End-to-end helpers for the Kinesis transaction ingestion path.

Exposed via :mod:`...api`:

- :func:`producer.produce` — generate N fakes, purge stream, push records,
  print one numbered line per record.
- :func:`consumer.consume` — drain every shard from ``TRIM_HORIZON`` and print
  one numbered line per record received.
- :func:`_kinesis.purge_stream` — drain-and-discard the stream contents (used
  internally by ``produce``; exposed for direct invocation as well).
"""
