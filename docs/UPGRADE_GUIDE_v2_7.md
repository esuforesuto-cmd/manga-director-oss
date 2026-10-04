# Upgrade Guide for v2.7 RC1

v2.7.0rc1 does not change public APIs, Project data, workflow semantics, or
configuration. v2.6.0 remains the stable baseline until the v2.7 final release
is approved.

Before testing the RC, back up local Project data, run repository integrity and
configuration validation, then exercise one normal Page workflow through
explicit approval. AI Director and Knowledge reports are advisory; they do not
replace `WorkflowEngine`, StateMachine validation, or human approval.

Rollback is package-level: reinstall the approved v2.6.0 artifact and retain
the existing Project data. No project-data migration is required. Hosted
adopters should retain their normal rollback, security, and evidence records.
