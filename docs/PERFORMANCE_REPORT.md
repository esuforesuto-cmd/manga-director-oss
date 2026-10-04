# v5.6 Performance Report

The local benchmark `benchmarks/manga_production_os_v5_6.py` measured 1,000
combined projections across the Production Pipeline and Story, Character, Page,
Review, and Export Engines.

| Measurement | Result |
| --- | ---: |
| 1,000 one-page read-only projections | 0.090212 s |

This is a local throughput indicator only. No v5.5 production-pipeline
baseline is available in this workspace, so it does not establish a comparative
no-regression claim. The benchmark performs no generation, filesystem writes,
repository I/O, publication, or workflow transition.
