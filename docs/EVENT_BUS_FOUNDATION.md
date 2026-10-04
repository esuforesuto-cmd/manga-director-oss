# Event Bus Foundation

## Purpose

The v5.2 Event Bus Foundation stores caller-supplied `AutomationEventDTO`
records so an automation preview can reference provenance and a Page. It is a
local registry, not an event-processing system.

## Boundaries

- Events are immutable metadata with an explicit producer, provenance, and
  Page reference.
- Duplicate identifiers are rejected deterministically.
- Reports always state that dispatch, queues, and retries have not started.
- There are no subscribers, handlers, replay, persistence, background tasks,
  network connections, or delivery guarantees.

An event therefore supplies review context only; it never advances a workflow
or causes a production action.
