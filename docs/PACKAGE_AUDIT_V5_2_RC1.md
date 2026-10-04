# v5.2.0 RC1 Package Audit

The RC package is built from dynamic version metadata in
`src/manga_director/_version.py`. Local validation covers wheel and source
distribution construction, metadata checking, package imports, typed marker,
LICENSE inclusion, optional extras declarations, and Automation Framework
exports.

The package contains local DTO and report code only; it introduces no network,
event-delivery, plugin-loading, distribution, or runtime-operation dependency.
