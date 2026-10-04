# Performance Tuning

## Built-in improvements

- Workflow context transitions copy only the changed top-level containers rather
  than deep-copying all retained artifacts.
- Metrics keep bounded duration summaries rather than an unbounded list of
  samples.
- Local repositories maintain metadata indexes; database repositories use
  Project/page and Project/state indexes plus paginated metadata reads.
- Database saves reconcile changed child records instead of deleting and
  recreating every Page/Chapter record.
- Sequential Batch execution stores compact progress/checkpoint/statistics
  records and reuses completed-page dependency state.

## Measurement

Run the provider-free scenarios from a checkout:

```text
PYTHONPATH=src python -m benchmarks.large_project
PYTHONPATH=src python -m benchmarks.repository_index
PYTHONPATH=src python -m benchmarks.database_query
PYTHONPATH=src python -m benchmarks.batch_resume
PYTHONPATH=src python -m benchmarks.workflow_scale
```

The v2.1 baseline file feeds a conservative regression smoke test. It detects
material regressions, not cross-machine throughput. Record hardware, Python,
OS, fixture size, iteration count, median, p95, and memory observation before
opening an optimization Issue.

## Do not tune around correctness

Never cache legal state transitions, skip persisted storyboards before image
generation, or bypass Quality Review/Human Approval. Core state correctness is
the performance boundary.
