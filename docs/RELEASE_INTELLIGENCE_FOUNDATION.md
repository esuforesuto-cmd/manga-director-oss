# Release Intelligence Foundation

v3.4 adds a read-only Release Intelligence projection with release health,
deployment, compatibility, regression, executive, and dashboard DTOs. It
aggregates supplied local Page evidence and the canonical installed version.

The service does not validate a release authoritatively, create a tag, sign,
publish, deploy, approve, remediate, or bypass the existing release checklist.
Publication remains a deliberate maintainer action after hosted release gates.

Use `manga-director director release-intelligence-v34 --project <id> --page
<number>`, the optional `/v3.4/release-intelligence` FastAPI provider, or the
`release_intelligence_v34` MCP tool.
