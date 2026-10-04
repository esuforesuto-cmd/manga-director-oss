# v5.1.0 Package Audit

The final package is built from `src/manga_director/_version.py` and validated
as both wheel and sdist. Metadata validation passes and both artifacts include
the typed marker, MIT LICENSE, Composition Engine, and Composition maturity
module.

The final wheel was installed into a dedicated local target and imported from
that target with `CompositionPlatformMaturityService`. Optional extras remain
declared in package metadata. No new network, plugin-loading, or execution
dependency was introduced.
