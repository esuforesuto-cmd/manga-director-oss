# v2.4.0 Production Deployment Guide

## Scope

v2.4.0 supports controlled local deployment through Application services and
repository ports. It does not provide Cloud control planes, distributed
workflow, remote provider execution, or credentials in `config.yaml`.

## Before startup

1. Select a configuration profile in the Configuration Layer.
2. Resolve credentials only from environment variables or a Secret Provider.
3. Validate configuration, repository availability, optional adapter
   registration, and dependency health before declaring readiness.
4. Preserve project backups and record a redacted configuration snapshot.

## During operation

Use `health summary`, `diagnostics report`, `provider check`, `backend check`,
and `repository check --project PROJECT_ID` for local evidence. These commands
must not generate images, invoke providers, or mutate a page state. Execute
all page changes through the existing WorkflowEngine-backed commands.

## Shutdown and recovery

Stop new work before shutdown, complete the configured graceful sequence, and
save through the Repository interface. On restart, validate the repository and
workflow consistency before resuming a Project, Chapter, Batch, or page. Never
repair workflow state by editing storage files directly.

## Release controls

Use the stable release checklist, SBOM, dependency license report, supported
version policy, security policy, and hosted CI evidence before production
promotion.
