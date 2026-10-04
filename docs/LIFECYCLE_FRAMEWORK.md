# Lifecycle Framework Design

## Common lifecycle record

Each planned lifecycle record describes a platform capability with an immutable identifier, owner, declared support phase, compatibility scope, evidence references, review date, and redaction classification. The record is a DTO and does not persist or transition anything by itself.

## Support phases

| Phase | Meaning | Required human evidence |
| --- | --- | --- |
| Planned | Design accepted but not shipped. | Architecture and compatibility review. |
| Active | New additive capability is supported. | Release evidence and owner. |
| Maintained | Supported with compatibility and defect focus. | Support policy and health review. |
| Deprecated | Supported replacement path is announced. | Notice, rationale, timeline, and migration guidance. |
| Retired | Historical record after an approved major-version change. | Final compatibility decision and archive reference. |

No v5.5 design action moves an existing component between phases. A future implementation must retain historical phase evidence and must treat unknown evidence as review-required rather than success.

## Review cadence

The framework proposes periodic human review of support scope, compatibility evidence, and open risks. It does not schedule jobs, notify users, or make operational decisions.
