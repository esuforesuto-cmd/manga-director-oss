# Enterprise Foundation

## Foundation scope

v6.0 designs enterprise readiness for teams that operate multiple projects and
workspaces. The first implementation remains local and opt-in; no Cloud SaaS,
identity provider, billing, or remote marketplace is introduced.

## Design pillars

- Workspace/project isolation by explicit scope identifiers.
- Role and policy references rather than a replacement authorization system.
- Audit-ready decision, review, automation, and extension provenance.
- Portfolio health, capacity, quality, and delivery summaries with redaction.
- Deployment profiles that keep local, enterprise, and extension capabilities
  composable.

## Deployment and extension strategy

Enterprise deployment is an adapter concern behind stable ports. A future
Plugin Marketplace reuses existing Plugin manifest, registry, validation, and
lifecycle contracts; discovery, installation, payment, and remote execution
are intentionally out of scope.
