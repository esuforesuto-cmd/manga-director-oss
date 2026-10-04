# Asset Management Foundation

`V43ProductionFoundationService.asset_management()` returns immutable planning
DTOs for an Asset, Asset Version, Asset Metadata, Dependency, and Asset Catalog
Summary. The report derives only supplied workflow-context evidence and does
not require a Repository-interface change.

| DTO | Planning purpose | Disabled boundary |
| --- | --- | --- |
| `V43AssetDTO` | Identifies one Page-scoped workflow-evidence asset. | Asset creation, storage, or persistence. |
| `V43AssetVersionDTO` | Describes a supplied version identifier. | Version creation or replacement. |
| `V43AssetMetadataDTO` | Lists supplied metadata keys and provenance presence. | Metadata mutation. |
| `V43DependencyDTO` | Lists supplied artifact references. | Dependency resolution or persistence. |
| `AssetCatalogSummary` | Counts local planning evidence. | Catalog storage or distribution. |

No download, upload, packaging, signing, distribution, Provider call, Backend
call, or external integration is available in this foundation.
