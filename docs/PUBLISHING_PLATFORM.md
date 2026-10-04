# Publishing Platform Design

## Scope

The v4.3 Publishing Platform plans human-reviewed hand-off evidence for an
Export Pipeline, Publishing Target, Distribution Channel, Release Schedule,
and Publication History. It does not export, publish, distribute, schedule,
tag, upload, or create releases.

## Proposed planning flow

```text
Approved one-Page evidence
        -> deliverable readiness plan
        -> export profile proposal
        -> target/channel compatibility finding
        -> human release schedule review
        -> publication-history record proposal
```

Every arrow is descriptive. The StateMachine still governs page approval, and
completed quality review remains mandatory before a Page can be approved.

## Proposed records

| Record | Purpose | Human decision required |
| --- | --- | --- |
| Export Plan | Describe formats, required evidence, and exclusions. | Approve any actual export. |
| Publishing Target | Describe target constraints and credentials boundary. | Authorize target use. |
| Distribution Channel | Compare channel requirements with supplied evidence. | Approve distribution. |
| Release Schedule | Present a non-executing proposed date/window. | Commit or schedule release. |
| Publication History | Preserve supplied human-confirmed event evidence. | Record durable history. |

## Security boundary

Plans must never contain credentials, tokens, private endpoints, or executable
commands. Target-specific integrations are out of scope until an explicit
security, permission, audit, and rollback design is approved.
