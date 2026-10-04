# Versioning Policy

`manga-director` follows Semantic Versioning.

- **MAJOR**: incompatible public Python API, CLI, persisted Project, workflow,
  Plugin, or Extension SDK change.
- **MINOR**: backward-compatible public capability, introduced only through an
  approved architecture and migration review.
- **PATCH**: compatible fixes, documentation, security, packaging, and
  maintenance improvements.
- **Pre-release**: PEP 440 Python pre-release identifiers such as `2.2.0rc1`;
  the frontend uses the corresponding npm form, such as `2.2.0-rc.1`.

## Version source of truth

Python's single source of truth is `src/manga_director/_version.py`.
`manga_director.__init__` and the local MCP server import that value; they do
not duplicate it. `pyproject.toml`, the frontend package metadata, SBOM,
release notes, and release-contract tests must match the release being built.

## Compatibility policy

Supported v1.x/v2.x public contracts follow
[Public API](PUBLIC_API.md) and [Supported Versions](../SUPPORTED_VERSIONS.md).
Deprecations require a documented replacement, a migration note, and at least
one supported release line before removal.
