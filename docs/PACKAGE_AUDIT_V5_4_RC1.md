# v5.4.0 RC1 Package Audit

The RC package is built from dynamic version metadata in
`src/manga_director/_version.py`. Local validation covers wheel and source
distribution construction, metadata checking, installation smoke, typed marker,
LICENSE inclusion, optional extras declarations, and Quality Framework exports.

The package introduces local DTO/report code only. It adds no network,
CI/CD-control, release-publication, or runtime-operation dependency.

## Local result

`manga_director-5.4.0rc1-py3-none-any.whl` and
`manga_director-5.4.0rc1.tar.gz` were built and passed `twine check`. The Wheel
was installed into a dependency-resolved local verifier; package import, CLI
help, MCP initialize version, and `pip check` all passed. A deliberately
dependency-free smoke environment cannot import the package because it omits
the declared SQLAlchemy runtime dependency; that environment is not a valid
installation configuration.
