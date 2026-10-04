# v3.3.0 Package Audit

The stable package uses dynamic Hatch versioning from
`src/manga_director/_version.py`. The typed package includes `py.typed`, README,
LICENSE, docs, examples, declared optional extras, SBOM, and dependency license
report. Wheel and sdist are built and checked before publication.

`3.3.0` is aligned with MCP and optional OpenAPI metadata and the SBOM. The
frontend uses the matching npm version `3.3.0`.

Final validation builds both artifacts, passes `twine check`, verifies the
wheel typed marker and version module, verifies README/docs/examples in the
sdist, and installs the wheel before CLI and MCP verification.
