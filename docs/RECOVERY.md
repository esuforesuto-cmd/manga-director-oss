# Recovery

Recovery is intentionally bounded to existing interfaces. `WorkflowRecovery`
loads one persisted page, asks the existing `WorkflowEngine` for exactly its
next legal step, and saves only after success. A failed step leaves the
persisted page unchanged.

`RepositoryRecovery.validate_for_resume()` verifies aggregate integrity before
an operator retries normal work. Batch and project resume preserve the existing
sequential, one-page scheduling rules. Provider and backend health failures are
reported as isolated runtime evidence; they never mutate workflow state.
