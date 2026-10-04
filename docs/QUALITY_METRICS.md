# Quality Metrics

## Metric model

Metrics are planned as deterministic calculations over supplied evidence. They
must expose numerator, denominator, unit, threshold, source set, and status so
that a reviewer can distinguish a failed check from missing evidence.

| Metric family | Illustrative measure | Use |
| --- | --- | --- |
| Review coverage | Completed required reviews / declared required reviews | Identify incomplete human review. |
| Validation coverage | Passed declared validations / declared validations | Summarize validation evidence. |
| Consistency | Compliant supplied checks / evaluated checks | Surface cross-artifact consistency findings. |
| Regression trend | Regressed checks / comparable checks | Highlight potential release risk. |
| Release readiness | Satisfied mandatory gates / mandatory gates | Produce an advisory release input. |

## Interpretation safeguards

- A denominator of zero or unknown source is `unknown`, not 100%.
- Thresholds and weighting come from `QualityPolicyDTO` and are reported.
- Metrics do not determine workflow state, approval, publication, or deployment.
- Historic comparisons require compatible policy revision and declared baseline.

## Reporting

The planned `QualityMetricsReportDTO` contains values, trends, findings, and
evidence references. JSON and Markdown are renderer concerns, not domain types.
