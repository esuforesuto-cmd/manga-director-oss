# Security

Security is an Application/Infrastructure layer. It provides interfaces for
authentication and authorization, environment/.env secret retrieval, validation,
sanitization, audit records, and in-memory fixed-window rate limiting. It never
makes Workflow or StateMachine decisions.

For an adapter-facing composition of these boundaries, see
[Security Framework](SECURITY_FRAMEWORK.md).

For static-token authentication and role-based authorization, see
[Authentication and Authorization](AUTHENTICATION_AUTHORIZATION.md).

For validated secret lookup and credential-safe references, see
[Secrets and Credential Management](SECRETS_CREDENTIAL_MANAGEMENT.md).

For read-only audit evidence and threat validation, see
[Security Audit and Threat Validation](SECURITY_AUDIT_THREAT_VALIDATION.md).

For a bounded security snapshot and human-response recommendations, see
[Security Monitoring and Incident Response](SECURITY_MONITORING_INCIDENT_RESPONSE.md).

For read-only security-compliance and release-readiness validation, see
[Security Compliance and Release Validation](SECURITY_COMPLIANCE_RELEASE_VALIDATION.md).
