# v5.4.0 Creative Quality Framework Summary

v5.4.0 makes Creative Quality Framework reporting available as an opt-in, human-gated capability.

## Included capability

- Quality Engine: quality rules, findings, scores, and summaries.
- Review Pipeline: review records and checklist-oriented diagnostics.
- Validation Engine: deterministic validation results and report DTOs.
- Quality Metrics and Release Criteria: quality and readiness reporting.
- Intelligence: trends, review analytics, validation insights, and continuous monitoring summaries.
- Governance: policy, audit, reliability, and lifecycle reporting.

## Operating boundary

All results are diagnostics for people and existing callers to review. They do not approve content, change workflow state, trigger CI/CD, publish artifacts, or make autonomous decisions.

## Adoption

The APIs are additive. Existing projects need no database, configuration, or workflow migration; consumers may opt in through the public SDK report helpers.
