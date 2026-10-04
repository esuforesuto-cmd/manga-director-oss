# v6.x Security Maintenance

## Local maintenance checks

For each maintenance change, validate affected boundaries, DTO inputs, package
metadata, SBOM parseability, common secret patterns, and regression coverage.
Keep Platform Policy and Governance reports human-gated and non-enforcing.

## Operational controls

External CVE review, hosted secret scanning, protected CI, artifact signing,
access control, and Marketplace publication require maintainer or deployment
authority. Their outcome must be recorded before a public maintenance release.

## Incident response

Security remediation must preserve the frozen v6.x API and StateMachine
authority. Use a compatible patch release and document any required operator
action without introducing automatic workflow execution.
