# manga-director v2.0.0rc1

## Highlights

v2 introduces Plugin and Extension SDK boundaries, LLM and image adapters,
prompt pipelines, Project/Chapter/Batch orchestration, MCP and Web UI delivery
surfaces, SQLAlchemy repository adapters, observability, notifications, and
security foundations.

## Compatibility

The v1 public Python API and forward-only Page workflow remain supported.
`run` stops at `QualityChecked`; explicit human approval is still mandatory.

## Known limitations

This release candidate excludes remote extension distribution, digital
signatures, real OAuth/JWT, distributed queues, real-time collaboration, and
production notification providers beyond Console/Mock/Webhook boundaries.

## Security

Do not store secrets in `config.yaml`. Use environment variables or `.env` in
local development. Review webhook allowed-host and private-network settings.
