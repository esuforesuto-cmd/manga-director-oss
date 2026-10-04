# v4.0.0 Package Audit

`pyproject.toml` derives the package version from
`src/manga_director/_version.py`, the single canonical Python source.
`manga_director.__init__` re-exports it; optional OpenAPI and MCP derive it at
runtime. The frontend and SBOM carry `4.0.0`.

Release validation builds wheel and sdist, verifies `py.typed`, README, MIT
License, optional extras, public exports, and clean-install CLI/MCP smoke. The
SBOM and dependency license report are release-review assets; distributors must
verify resolved licenses in the exact publication environment.
