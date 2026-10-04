# v5.1.0 RC1 Package Audit

The RC package is built from dynamic version metadata in
`src/manga_director/_version.py`. Validation covers wheel and source
distribution construction, metadata checking, package imports, typed marker,
LICENSE inclusion, optional extras declarations, and Composition Platform
exports.

The package contains local DTO and report code only; it has no new network,
plugin-loading, distribution, or runtime-operation dependency.
