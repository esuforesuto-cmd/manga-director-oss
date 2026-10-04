# Asset Cache

`AssetCache` is an explicit, process-local cache of immutable Asset Manager
reports. `V57ProductionWorkspaceService.asset_cache()` derives a key from one
Page's project identifier, state, and artifact or metadata key set, then
reuses only the matching report.

The cache can be refreshed or invalidated by its owner. It never persists
entries, reads or writes asset storage, mutates a Repository, or changes a
workflow state.
