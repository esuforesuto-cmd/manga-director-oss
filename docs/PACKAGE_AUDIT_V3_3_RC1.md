# v3.3.0 RC1 Package Audit

The RC package uses dynamic Hatch versioning from
`src/manga_director/_version.py`. The typed package includes `py.typed`, README,
LICENSE, docs, examples, declared optional extras, SBOM, and dependency license
report. Wheel and sdist are built and checked before publication.

`3.3.0rc1` is aligned with MCP and optional OpenAPI metadata and the SBOM. The
frontend uses the equivalent npm prerelease `3.3.0-rc.1`.

Local RC validation built both artifacts, passed `twine check`, verified the
wheel's typed marker and version module, verified README/docs/examples in the
sdist, and installed the wheel before CLI verification.
