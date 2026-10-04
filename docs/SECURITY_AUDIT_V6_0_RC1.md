# v6.0 RC1 Security Audit

## Local scope

The RC audit covers v6.0 Platform Foundation, Intelligence, and Platform Kernel
source boundaries, DTO validation, one-Page StateMachine preservation, SBOM
parseability, and common secret-pattern scanning.

## Boundary posture

The v6 modules introduce no network client, credential, Provider, Backend,
repository, delivery-adapter, workflow-engine execution, extension loading,
marketplace publication, policy-enforcement, or telemetry path.

External CVE lookup, hosted secret scanning, signing, and protected CI remain
maintainer-controlled validations.
