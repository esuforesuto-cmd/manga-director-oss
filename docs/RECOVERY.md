# Recovery

Recovery is intentionally bounded to existing interfaces. `WorkflowRecovery`
loads one persisted page, asks the existing `WorkflowEngine` for exactly its
next legal step, and saves only after success. A failed step leaves the
persisted page unchanged.

`RepositoryRecovery.validate_for_resume()` verifies aggregate integrity before
an operator retries normal work. Batch and project resume preserve the existing
sequential, one-page scheduling rules. Provider and backend health failures are
reported as isolated runtime evidence; they never mutate workflow state.

`WorkflowRecovery.resume_step` currently loads with the private
`ProjectLoader._load_for_execution()` path and then calls `ProjectLoader.save()`
without a revision compare-and-swap. This helper validates the persisted Project
identity and requested Page, plus reserved storyboard authority in persisted
metadata and history, before using the loader's overridable `load()` projection.
The execution context's identity and reserved metadata are checked afterward.
On a raw LocalFile Project that has not been framed or activated, concurrent
writes through this helper can lose an intervening update because the save has
no revision check. Serialize writers for the same Project through the helper's
complete load–execute–save cycle.
The legacy P2 limitation is tracked in `docs/V7_17_PR82_RESOLUTION.md`.
Standard durable LocalFile CLI/HTTP storyboard confirmation uses its separate
fenced command path and is outside this recovery helper.
