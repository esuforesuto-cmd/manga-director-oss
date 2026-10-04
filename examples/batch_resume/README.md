# Batch Resume

Run the deterministic sequential resume benchmark from a development checkout:

```text
PYTHONPATH=src python -m benchmarks.batch_resume
```

The scenario deliberately fails one page, records a checkpoint, resumes only
pending work, then retries failed work. It never uses parallel execution. See
[Batch Guide](../../docs/BATCH_GUIDE.md).
