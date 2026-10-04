# Security Framework

`SecurityFramework` composes the existing authentication, authorization,
validation, rate-limit, and audit boundaries for adapter-facing access checks.

## Decision flow

For each `authorize` call, the framework authenticates the supplied
credentials, evaluates an optional rate limiter, evaluates the authorization
policy, and records the result in an `AuditLogger`. An absent authorization
policy denies access by default.

The framework returns an immutable `SecurityDecision`; it does not mutate a
project, execute a workflow, advance the StateMachine, load a plugin, or
persist any record outside the caller-provided audit logger.

## Usage

Provide implementations of `AuthenticationProvider` and `AuthorizationPolicy`
at an application boundary. `RateLimiter`, `SecurityValidator`, and
`AuditLogger` are optional collaborators; defaults are supplied for validation
and in-process audit records. `validate_identifier` delegates to the configured
validator. Existing security classes remain available for direct use.
