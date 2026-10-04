# Authentication and Authorization

The security package provides composable, adapter-facing authentication and
authorization boundaries. They do not mutate projects, transition workflow
state, or replace the StateMachine.

## Static token authentication

`StaticTokenAuthenticationProvider` maps caller-supplied non-empty tokens to
principals. It is suitable for local or explicitly configured deployments; load
tokens through the existing secret-management boundary rather than storing them
in project files.

## Role authorization

`RoleAuthorizationPolicy` maps principals to roles and roles to exact action
names. Access is denied when a principal has no assigned role or no matching
permission. The policy intentionally does not grant wildcard permissions.

## Security Framework integration

Pass both implementations to `SecurityFramework` to authenticate and authorize
an adapter request in one auditable decision. Existing `NoAuthProvider` and
`AllowAllPolicy` remain development-only compatibility utilities.
