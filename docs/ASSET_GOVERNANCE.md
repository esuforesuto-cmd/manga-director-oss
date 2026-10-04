# Asset Governance

Asset Governance uses the current Repository-derived lifecycle projection to
describe redaction, Repository-port, and no-implicit-mutation controls. It
reports bounded identifiers and counts only; metadata values are not surfaced.

Retention is intentionally a human policy decision. The service never evaluates
or applies retention, creates versions, archives, deletes, repairs, resolves
dependencies, or persists an asset change. Use `director asset-governance-v33`,
`GET /v3.3/asset-governance`, or MCP `asset_governance_v33`.
