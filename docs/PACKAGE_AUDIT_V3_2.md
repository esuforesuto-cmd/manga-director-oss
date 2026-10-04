# v3.2.0 Package Audit

The stable package uses dynamic Hatch versioning from
`src/manga_director/_version.py`; `pyproject.toml` deliberately does not repeat
the version. The typed package includes `py.typed`, README, LICENSE, docs,
examples, declared optional extras, SBOM, and dependency license report. Wheel
and sdist are built and checked before publication.

`3.2.0` is aligned with MCP and optional OpenAPI metadata and the SBOM. The
frontend uses the same stable npm version, `3.2.0`.
