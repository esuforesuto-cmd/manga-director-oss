# Health History

`HealthHistoryStore` persists bounded operational snapshots in the existing
Project aggregate's metadata through `ProjectRepository`. No concrete
Repository, database table, or Core Domain behavior is required.

Supported scopes are `configuration`, `provider`, `backend`, and `runtime`.
Each immutable snapshot has a capture time, boolean health result, and safe DTO
details. The default per-Project limit is 100 entries; the oldest entries are
discarded when the bound is exceeded.

```python
history.record("project-id", "runtime", True, {"mode": "local"})
timeline = history.timeline("project-id", "runtime")
```

Timeline data is operational evidence only. It cannot recover, transition,
approve, schedule, or otherwise control a Page workflow.
