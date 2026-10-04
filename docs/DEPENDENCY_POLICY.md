# Dependency Policy

Dependencies are declared in `pyproject.toml`; optional capabilities are kept
in named extras. The readiness facade reports declarations and confirms that
the checked-in dependency license report exists. It does not query registries,
perform vulnerability scanning, or modify the environment.

Before a release, maintainers should review package metadata, optional extras,
the [dependency license report](DEPENDENCY_LICENSE_REPORT.md), compatibility
requirements, and the SBOM. Dependency upgrades must preserve the documented
public API and pass the established quality gates.
