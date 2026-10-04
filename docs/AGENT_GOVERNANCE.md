# Agent Governance Foundation

v4.1 adds policy, permission, capability-restriction, governance-report, and
compliance-summary DTOs for registered agent declarations. These records are
local, immutable governance evidence, not an authorization system.

`V41PlatformAssuranceService.governance()` does not grant permissions, store
policies, enforce restrictions, invoke agents, or change their capabilities.
Human administrators retain responsibility for every policy decision.

## Safety boundary

- No permission or capability restriction is enforced.
- No policy or compliance assessment is persisted or externally attested.
- Governance cannot dispatch work, transition a workflow, alter a Repository,
  or approve a Page.
