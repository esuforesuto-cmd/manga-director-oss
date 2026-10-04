# v4.4 Security Audit

Final review confirms that immutable Pydantic DTO validation protects the
Enterprise Platform boundary. The platform has no delivery, repository, or
execution-layer dependency; Marketplace and Extension Registry cannot discover,
download, install, load, execute, publish, pay, bill, or call external
services. Governance cannot enforce policy or approve content, and Reliability
cannot monitor, alert, retry, or recover.

The local dependency audit reported **no known vulnerabilities** among auditable
installed dependencies. The editable `manga-director` package is excluded
because it is not a published PyPI dependency. Hosted secret scanning, signed
artifacts, and registry CVE scans remain maintainer-controlled publication
steps.
