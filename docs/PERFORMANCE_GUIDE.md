# Performance Guide

## Current baseline

Use the provider-free smoke suite as a regression indicator:

```text
PYTHONPATH=src python -m benchmarks.smoke
```

It covers Workflow, Repository, SQLite database, Prompt, mock LLM, mock Image,
mock Notification, and Batch planning. It does not measure network latency or
assert a machine-independent budget.

## Measuring an Issue

Record the commit, Python version, OS, CPU, storage, database URL, project/page
count, cache state, iteration count, median, p95, and memory observation. Use
mock providers for Core measurements. Include a rollback threshold and prove
that one-page workflow and approval invariants are unchanged.

## Planned benchmark backlog

| Boundary | v2.2 measurement question |
| --- | --- |
| Workflow | How does step latency change with realistic artifact size? |
| Repository | What are save/load/list costs across project and history sizes? |
| Database | Which queries or pool settings dominate SQLite/PostgreSQL workloads? |
| LLM / Image | What adapter overhead exists without external latency? |
| Notification | What retry cost exists under deterministic failure simulation? |
| Automation | Not measurable until a separately approved runtime exists. |
| Plugin | What discovery, manifest, and composition cost scales with plugin count? |
