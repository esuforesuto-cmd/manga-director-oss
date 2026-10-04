# v3.1.0 RC1 Package Audit

The RC package uses dynamic Hatch versioning from
`src/manga_director/_version.py`. The typed package includes `py.typed`, README,
LICENSE, docs, examples, declared optional extras, SBOM, and dependency license
report. Wheel and sdist must be built and checked before publication.

`3.1.0rc1` is aligned with MCP/optional OpenAPI metadata and SBOM. The frontend
uses the equivalent npm prerelease `3.1.0-rc.1`.
