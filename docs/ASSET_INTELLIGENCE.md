# Asset Intelligence Planning

Asset Intelligence is a Repository-derived evidence layer for creative assets.
It must preserve existing artifact ownership and never infer a write, remote
fetch, model call, or workflow transition.

| Candidate | Design boundary | Required evidence before implementation |
| --- | --- | --- |
| Asset Catalog | Inventory existing artifact references. | Ownership, retention, and pagination policy. |
| Asset Metadata | Project safe metadata fields and provenance. | Redaction and schema-compatibility policy. |
| Asset Relationship | Describe explicit identifiers and links. | Cycle, deletion, and cross-project policy. |
| Asset Search | Filter bounded local projections. | Deterministic ordering and no semantic remote lookup. |
| Asset Versioning | Describe version/snapshot evidence. | Provenance, retention, and human resolution policy. |
| Asset Usage Analytics | Aggregate reference and use counts. | Observation window, privacy, and no-optimization proof. |

## v4.3 Iteration 2 intelligence

`V43ProductionIntelligenceService.asset_intelligence()` turns v4.3 catalog
evidence into immutable Asset Analysis, Dependency Analysis, Asset Usage,
Duplicate Detection, and Asset Insight Summary DTOs. It analyzes supplied
metadata and artifact reference names only.

The report never resolves dependencies, changes usage, removes a duplicate,
persists analysis, alters an asset/version, downloads content, packages,
uploads, or distributes an asset. Duplicate findings are empty local
observations unless future, separately approved evidence supplies candidates.
