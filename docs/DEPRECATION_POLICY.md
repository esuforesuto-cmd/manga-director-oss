# Deprecation Policy Design

## Policy intent

Deprecation is a communication and evidence process, not an automatic removal mechanism. A capability remains supported until an approved compatibility decision in a future release changes that status.

## Required notice record

Every planned deprecation must identify the affected public surface, replacement or rationale, compatibility impact, earliest removal release, migration guidance, exception process, owner, and review date.

## v6 LTS commitments

- v5.x compatibility contracts and v6.0 frozen Platform API, SDK, Extension,
  and Marketplace descriptor contracts are not removed by v6.x LTS work.
- v6.x changes remain additive unless a separately approved major-version plan
  documents a migration path.
- Warnings, errors, feature disabling, package removal, and data deletion are outside this design.
- The StateMachine and one-Page workflow invariants are not deprecation candidates.

## Review model

The lifecycle report may mark a notice as complete, incomplete, or unknown. Human release and governance owners decide whether to communicate or act on it; the report cannot enforce a policy.
