# Creative Quality Framework

## Purpose

The framework is a planned diagnostic contract that unifies quality policy,
evidence, metrics, findings, and a human-readable recommendation for one
declared scope. It fails closed: unavailable or malformed evidence is reported
as `unknown` or `blocked`; it is never silently corrected.

## Planned DTO boundary

| DTO | Meaning |
| --- | --- |
| `QualityPolicyDTO` | Named policy revision, owner, required checks, and threshold declarations. |
| `QualityEvidenceDTO` | Immutable reference to supplied review, test, workflow, or governance evidence. |
| `QualityMetricDTO` | Metric name, value, unit, threshold, source, and calculation status. |
| `QualityFindingDTO` | Deterministic severity, rationale, affected scope, and required human action. |
| `QualityRecommendationDTO` | Advisory readiness recommendation with evidence identifiers. |
| `QualityFrameworkReportDTO` | Transport-neutral aggregation for a human reviewer. |

## Rules

1. A report has one clearly declared Page or release scope; it cannot combine
   multiple workflow Page requests.
2. Every recommendation carries evidence references and no action command.
3. A missing completed quality review prevents a Page-approval recommendation.
4. Thresholds are policy input, not hidden framework defaults.
5. A report cannot persist a decision, modify a project, or invoke CI/CD.

## Adoption sequence

Start with a static policy and supplied local evidence, validate DTO contracts,
then publish JSON/Markdown renderers as adapters. Runtime enforcement, policy
editing, and automatic remediation remain separate future decisions.
