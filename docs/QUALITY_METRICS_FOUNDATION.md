# Quality Metrics Foundation

`QualityMetricsFoundation` produces transparent `QualityMetricDTO` values from
supplied validation evidence. The initial `validation_coverage` metric retains
its numerator, denominator, status, and evidence references.

Empty evidence is `unknown`, not a passing score. The service does not retain
history, alter thresholds, generate trends, or change a workflow.
