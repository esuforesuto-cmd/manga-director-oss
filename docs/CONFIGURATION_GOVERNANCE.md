# Configuration Governance

Configuration remains owned by the configuration layer. `AppConfig.schema_version` identifies the schema, and `configuration_governance()` returns a safe compatibility, integrity, migration, and fingerprint report.

The fingerprint is calculated from the redacted configuration snapshot, so credentials and database URLs are never exposed in reports. An incompatible schema is reported as requiring migration; automatic migration is intentionally not performed in v2.3.

Enterprise profiles can remain read-only through `require_writable_configuration()`.
