# Profiling

Start with the deterministic smoke harness:

```bash
PYTHONPATH=src python -m benchmarks.smoke
```

For a targeted CPU profile, use the standard library:

```bash
PYTHONPATH=src python -m cProfile -o profile.pstats -m benchmarks.smoke
python -c "import pstats; pstats.Stats('profile.pstats').sort_stats('cumulative').print_stats(30)"
```

Profile one boundary at a time: workflow transition, repository serialization,
database persistence, prompt rendering, or a mock adapter. Never include API
keys, tokens, webhook signatures, project secrets, or production payloads in
profile artefacts. `profile.pstats` is ignored by Git.
