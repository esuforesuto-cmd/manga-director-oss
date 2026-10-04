# Quality Checks Example

Use the project quality commands from the checkout root:

```text
ruff check .
mypy src
pytest
python -m benchmarks.smoke
```

For a change that touches production, Provider, Backend, configuration, or
upgrade boundaries, also collect the matching quality-gate evidence from
[Quality Assurance](../../docs/QUALITY_ASSURANCE.md). These checks are
provider-free and must not require secrets or network calls.
