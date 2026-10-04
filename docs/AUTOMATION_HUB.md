# Automation Hub

## v6.0 Iteration 2 foundation

The Automation Hub compares caller-supplied advisory rules with the
StateMachine-validated next command. It exposes matching rule identifiers as
planning evidence and requires human review for every rule.

Rules are neither registered nor executed. The hub does not subscribe to
events, schedule work, dispatch automation, or mutate a workflow.

## Compatibility

Automation Hub is an additive diagnostic projection; existing Automation,
Workflow, Plugin, CLI, FastAPI, MCP, and Web UI contracts remain intact.
