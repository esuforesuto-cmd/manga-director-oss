# v3.1.0 Package Audit

The package uses dynamic Hatch versioning from
`src/manga_director/_version.py`. The typed distribution includes `py.typed`,
README, LICENSE, docs, examples, declared optional extras, SBOM, and the
dependency license report. Wheel and sdist are built and checked with Twine;
a clean environment installs the wheel and starts the CLI and MCP server.

`3.1.0` is aligned with MCP, optional OpenAPI metadata, frontend metadata, and
SBOM through the canonical version source.
