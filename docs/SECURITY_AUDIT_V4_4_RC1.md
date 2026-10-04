# v4.4 RC1 Security Audit

## Reviewed boundaries

- DTO validation is provided by immutable Pydantic models.
- Enterprise modules have no direct dependency on delivery, repository, or
  execution layers.
- Marketplace and Extension Registry projections cannot discover, download,
  install, load, execute, publish, pay, bill, or call external services.
- Governance cannot enforce policy or approve content; Reliability cannot
  monitor, alert, retry, or recover.
- Workflow safety remains owned by the domain StateMachine.

## Dependency audit

The local dependency audit completed against the installed release-validation
environment with the editable `manga-director` package excluded (it is not a
published PyPI dependency). The audit reported **no known vulnerabilities**.
Registry publication, signing, and hosted secret/CVE scanning remain
maintainer-controlled steps.

See the [release checklist](RELEASE_CHECKLIST_V4_4_RC1.md).
