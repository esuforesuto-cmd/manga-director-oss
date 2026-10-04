# Production Checklist

`ProductionReadinessReport` renders these checks as JSON and Markdown without
performing deployment work.

## Deployment

- Validate the redacted configuration fingerprint and dependency health.
- Confirm local Provider and Image Backend inventory health.
- Run the Repository integrity self-check for a representative Project.

## Upgrade

- Validate the incoming configuration export before applying it.
- Back up Project data before changing package or deployment versions.
- Run a read-only recovery simulation against a representative Page.

## Backup and recovery

- Keep a tested Repository backup procedure for the chosen adapter.
- Capture an integrity report after restore.
- Resume only the one Page step admitted by `WorkflowEngine` and `StateMachine`.

This checklist is deployment-neutral: it does not include cloud services,
distributed workers, credential provisioning, or automated remediation.
