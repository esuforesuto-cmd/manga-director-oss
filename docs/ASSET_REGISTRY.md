# Asset Registry v1

`V57ProductionWorkspaceService.asset_registry()` turns the existing v5.7
Asset Manager evidence into a deterministic, read-only inventory. Entries
identify artifact and metadata provenance for exactly one Page.

The registry does not create, version, archive, distribute, or persist assets.
Existing Asset DTOs and Repository interfaces remain authoritative.

`unique_source_keys` is a compact index only. Registry entries preserve
`source_kind`, so Artifact and Metadata evidence sharing the same key remain
separate, traceable records.
