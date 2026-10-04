# End-of-Life Policy

## Lifecycle transition

An LTS line remains supported until maintainers publish an end-of-life notice.
The notice identifies the affected line, final supported version, reason for
transition, successor line or maintenance recommendation, migration guidance,
security support end, and a contact path for clarification.

## Notice requirements

End-of-life is not retroactive. Maintainers publish the notice in the release
notes, [SUPPORTED_VERSIONS.md](SUPPORTED_VERSIONS.md), and roadmap before the
support status changes. Existing workflow invariants and archived API reference
documents remain available for operators planning migration.

## After end-of-life

No further compatibility, security, or maintenance guarantee applies to the
retired line. Critical fixes may be evaluated separately but do not re-open the
support lifecycle without an explicit maintainer decision.
