# v3.4.0 RC1 Package Audit

The RC package uses dynamic Hatch versioning from
`src/manga_director/_version.py`; `pyproject.toml` intentionally avoids a
second version value. The typed package includes `py.typed`, README, LICENSE,
docs, examples, declared optional extras, SBOM, and dependency license report.
Wheel and sdist are built and checked before publication.

`3.4.0rc1` is aligned with MCP and optional OpenAPI metadata and the SBOM. The
frontend uses the equivalent npm prerelease `3.4.0-rc.1`.

Local RC validation builds both artifacts, passes `twine check`, verifies the
wheel's typed marker and version module, verifies README/docs/examples in the
sdist, and installs the wheel before CLI and MCP verification.
