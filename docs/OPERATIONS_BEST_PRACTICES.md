# Operations Best Practices

## Safe operating boundary

Use health, diagnostics, repository checks, and production-readiness reports
for observation. Use existing WorkflowEngine-backed Project, Chapter, Batch,
and page commands for state changes. Do not edit persisted state, invoke an
Agent directly, or use a diagnostic report as a recovery command.

## Before execution

1. Select and validate a configuration profile.
2. Resolve secrets through environment variables or a Secret Provider, never
   through `config.yaml` or project metadata.
3. Verify repository availability and record a redacted configuration snapshot.
4. Confirm the Page has the expected persisted state before selecting a step.

## During execution

- Produce exactly one Page per workflow execution.
- Preserve the forward-only sequence; a correction is a same-state re-run.
- Require a persisted storyboard before generation and a completed quality
  review before explicit human approval.
- Export only redacted diagnostics and retain them under local access policy.

## Recovery and shutdown

Validate repository integrity and workflow consistency before resume. Stop new
work before graceful shutdown, save through the Repository port, and document
the operator decision. Recovery simulation is evidence only; it never repairs
or advances a Page.
