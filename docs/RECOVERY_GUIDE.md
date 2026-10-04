# Recovery Guide

Use `ReliabilityOperations` before a manual resume. It composes the existing
`ProjectIntegrityChecker`, `RepositorySelfCheck`, `RepositoryRecovery`,
`ProjectLoader`, and `WorkflowEngine` without modifying any of them.

1. Call `validate_resume(project_id, page_number)` to check aggregate integrity,
   persisted workflow-history consistency, and the next legal step.
2. Call `simulate_recovery(...)` to produce a plan. Simulation is read-only and
   never invokes an Agent or saves a Project.
3. Review `recovery_report(...)`, which includes the Repository self-check and
   simulation evidence as JSON or Markdown.
4. Only after a successful review, use the existing Workflow recovery path to
   execute exactly one legal Page step.

An approved Page is terminal and is therefore reported as non-resumable. A
failed validation must be repaired by an operator; this module does not repair,
rewrite history, or bypass the StateMachine.
