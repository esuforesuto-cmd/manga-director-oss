# Migration Strategy: v5.1 to v5.2

## Status

v5.2.0 is an additive stable release. No data conversion, configuration update,
rule adoption, event setup, or workflow migration is required.

## Compatibility promise

v5.0 LTS and v5.1 public contracts remain supported. Existing Python API, CLI,
FastAPI/REST, MCP, Web UI, Repository, Workflow, SDK, Provider, and Backend
users can retain their current integration with no Automation Framework
metadata.

## Optional adoption path

1. Keep the existing v5.1 integration unchanged.
2. Optionally describe a local template, event, or rule.
3. Generate a planning or maturity preview and have a named human review it.
4. Compare it with legacy contract-equivalence and workflow-invariant fixtures.
5. Roll back by removing optional metadata; no data, event, or workflow rollback
   is needed because the planning plane owns none of them.

## Required evidence for optional adoption

- Public-surface fixtures across Python, CLI, FastAPI/REST, MCP, Web UI,
  Repository, Workflow, and SDK.
- StateMachine tests covering one Page, complete stages, persisted storyboard,
  and completed quality review before approval.
- Offline template, event, rule, plan, and governance validation with no
  service invocation or persistence.

Remote dispatch, scheduling, execution, policy enforcement, hosted events, and
automation operations remain deferred.
