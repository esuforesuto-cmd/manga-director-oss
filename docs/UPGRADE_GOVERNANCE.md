# Upgrade Governance

`UpgradeGovernanceReport` evaluates human-owned upgrade policy against supplied LTS compatibility, compatibility evidence, and rollback references. A compliant result means the evidence can be reviewed by an authorized owner; it is not permission to upgrade.

The service never installs a package, changes configuration, runs data migration, performs rollback, signs an artifact, or changes a release process. v5.0 LTS compatibility remains a required evidence boundary.
