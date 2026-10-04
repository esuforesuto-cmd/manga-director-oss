# Release Validation

Release validation composes the quality pipeline and production-quality summary
without coupling to CLI, FastAPI, MCP, or Web UI. It verifies that:

- package metadata reads the canonical `_version.py` source;
- the SBOM package version matches the installed-source version;
- required release assets exist and local documentation links resolve;
- root API exports match the compatibility contract; and
- repository maintenance and workflow validation remain healthy.

The DTOs are local pre-release evidence only. Before publishing, the exact tag
must still pass hosted CI, clean dependency/CVE and secret scans, artifact
validation, and the release checklist.
