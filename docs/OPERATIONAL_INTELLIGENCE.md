# Operational Intelligence Design

## Purpose

Operational Intelligence is a read-only v4.8 design for summarizing supplied
signals from Workspace, Agent Platform, Knowledge, Production, Enterprise, and
Decision Platform reports. It helps a human understand operating conditions;
it does not operate the system.

## Common indicators

| Indicator | Example inputs | Advisory question |
| --- | --- | --- |
| Scope health | Workspace activity, project and Page references. | Is the current creative scope clear and one-Page safe? |
| Knowledge health | Provenance, coverage, consistency, graph, and lifecycle reports. | Is supporting knowledge sufficient and traceable? |
| Production health | Pipeline, quality, asset, deliverable, and capacity reports. | Where should a human review bottlenecks or risk? |
| Decision health | Alternatives, review coverage, approval readiness, and trace reports. | Are prerequisites explicit before a human decides? |
| Enterprise health | Governance, reliability, portfolio, and organization evidence. | Which policy or operational questions need ownership? |

## Report boundary

An aggregate report may calculate declared, deterministic rollups from supplied
values and retain source links, confidence, freshness, and redaction markers.
It cannot collect telemetry, probe health, monitor or alert, write a dashboard,
schedule work, change capacity, enforce policy, select a recommendation,
approve content, mutate workflow state, retry/recover, call a Provider, or
contact an external service.

## Data minimization

Only summaries and references necessary for the requested human review should
cross a module boundary. Original content, credentials, personal data, and
unredacted knowledge remain in their owner module. Consumers must preserve
caller-supplied provenance and may only render redacted data.

## Operational review loop

1. A human requests a bounded summary and supplies approved source reports.
2. The platform presents uncertainty, freshness, missing evidence, and
   ownership—not an automatic action.
3. The human uses existing CLI, API, MCP, or Web UI workflows to take any
   authorized action.
4. Existing StateMachine, review, and repository rules validate that action.
