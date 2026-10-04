# Release Governance

## Purpose

Release Governance defines a planned release-decision packet combining quality,
compatibility, security, documentation, package, and human sign-off evidence.
It is advisory only and cannot operate CI/CD, create tags, sign artifacts,
upload packages, or publish a release.

## Planned release criteria

| Criterion | Required evidence | Result when absent |
| --- | --- | --- |
| Compatibility | Versioned Python API, CLI, FastAPI, MCP, workflow, and repository checks | `blocked` |
| Quality | Completed review and quality-gate evidence | `blocked` |
| Security | Dependency/audit results and issue disposition | `needs_review` |
| Package | Build/install and export evidence | `needs_review` |
| Documentation | Link and surface review evidence | `needs_review` |
| Approval | Explicit authorized human sign-off | `blocked` |

## Governance contract

`ReleaseGovernanceReportDTO` should record policy revision, evidence IDs,
exceptions, residual risks, and a recommendation (`do_not_release`,
`needs_review`, or `release_candidate`). The recommendation is not a command;
the existing release process retains all authority.

## LTS protection

Every future v5.4 quality release criterion must include a v5.0 LTS
compatibility evidence slot. No policy may require configuration, package,
workflow, or API migration for legacy consumers.
