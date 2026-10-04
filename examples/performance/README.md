# Performance example

Run `PYTHONPATH=src python examples/performance/smoke.py`. This exercises one
mock/provider-free workflow operation and reports a local regression signal.
For the full development-checkout benchmark harness, use
`PYTHONPATH=src python -m benchmarks.smoke`. Neither result is a cross-machine
performance claim; see the [Performance Guide](../../docs/PERFORMANCE_GUIDE.md).
