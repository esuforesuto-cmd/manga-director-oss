# v3.4.0 Package Audit

`pyproject.toml` derives the package version from
`src/manga_director/_version.py`, which is the single canonical Python source.
`manga_director.__init__` re-exports it; optional OpenAPI and MCP derive it at
runtime. The frontend and SBOM carry `3.4.0`.

Validated release artifacts are wheel and sdist. The wheel includes `py.typed`,
and the source distribution includes the README and MIT License. Optional extras
remain declared in project metadata. The SBOM and dependency license report are
included as release-review assets; distributors must verify resolved licenses in
the publication environment.
