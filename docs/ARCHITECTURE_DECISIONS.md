# Architecture Decisions

## ADR-001: Page StateMachine is authoritative

All delivery adapters delegate transitions to WorkflowEngine/StateMachine.

## ADR-002: Extension boundaries are additive

Plugins and SDK extensions use published contracts and cannot bypass approval.

## ADR-003: Delivery layers remain thin

CLI, API, MCP, and Web UI do not own workflow logic.
