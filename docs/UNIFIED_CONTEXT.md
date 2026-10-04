# Unified Creative Context

## Purpose

Unified Creative Context normalizes references used by existing reports without
making a shared memory store. It provides stable correlation across Workspace,
Knowledge, Agents, Production, Enterprise, Decision, and Ecosystem modules.

## Proposed reference model

| Field | Meaning | Compatibility rule |
| --- | --- | --- |
| `project_id` | Existing Project identifier. | Never remap identifiers. |
| `page_reference` | Exactly one existing Page reference. | Required for workflow-scoped reports. |
| `session_id` | Optional existing workspace/agent/review session reference. | No new session lifecycle. |
| `correlation_id` | Caller-supplied trace correlation token. | No telemetry collection. |
| `owner_module` | Source-of-truth module for each item. | Existing owner remains authoritative. |
| `source_reference` | Repository or report reference. | No implicit load or persistence. |
| `freshness` | Supplied observation/snapshot time and status. | Never infer data recency. |
| `redaction` | Caller-selected visibility label. | Does not grant access or enforce policy. |

## Context boundaries

Context is immutable, caller-supplied, and DTO-only. It cannot retain long-term
memory, merge knowledge, authorize participants, fetch data, synchronize with
an external system, or change StateMachine state. A future implementation must
keep existing Knowledge and Repository interfaces untouched.

