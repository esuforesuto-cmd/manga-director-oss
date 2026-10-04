# Migration Strategy: v4.x to v5.0

## Release status

v5.0.0 is an additive, no-conversion release. v4.8 users continue without code
or configuration changes and may adopt Unified Platform reports voluntarily.

## Migration principles

1. Preserve all v4.8 public contracts and support v4.x integrations.
2. Introduce unified DTOs and facades as optional additions only.
3. Keep existing identifiers, repositories, persistence formats, and source
   ownership unchanged.
4. Prove legacy/facade equivalence before a facade is recommended.
5. Announce any future deprecation with a documented support window; v5.0.0
   removes nothing and requires no forced conversion.

## Incremental adoption path

| Stage | Consumer action | Required proof |
| --- | --- | --- |
| 0 — remain on v4 API | None. | Existing v4 contract suite stays green. |
| 1 — read unified reports | Opt in to an additive DTO/facade. | Source/provenance and report-equivalence checks. |
| 2 — adopt SDK helpers | Replace local composition code voluntarily. | Error/DTO/transport compatibility tests. |
| 3 — review aliases | Consider documented aliases after support review. | Consumer migration feedback and no behavior change. |

## Data and rollback

No shared database, repository migration, or data rewrite is planned. Unified
reports reference owner records and do not copy, merge, delete, or mutate them.
Disabling an optional facade returns a consumer to its current v4.x interfaces
without data conversion.
