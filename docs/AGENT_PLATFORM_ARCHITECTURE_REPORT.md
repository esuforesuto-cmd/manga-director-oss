# Agent Platform Architecture Report

## Decision

v4.1 is approved as a design-only planning cycle for a Creative Agent Platform.
The proposed Multi-Agent Framework, Creative Collaboration, Agent
Orchestration, and Human-in-the-Loop models are reviewable without adding
execution authority.

## Architecture outcome

The design places immutable Agent planning DTOs in the Application layer above
the existing Creative Workspace, Memory, Graph, and Quality projections. The
Core StateMachine, Workflow Engine, Repository ports, Provider interfaces,
Plugin boundary, Extension SDK, CLI, FastAPI, MCP, and Web UI remain unchanged.

## Issue-ready work packages

| Package | Priority | Estimate | Dependency | Exit criterion |
| --- | --- | --- | --- | --- |
| Registry vocabulary | Must | S | v4 DTO conventions | Typed, read-only profile/capability/role/lifecycle/protocol DTOs. |
| Collaboration planning | Must | M | Registry vocabulary | Five role proposals with explicit human checkpoints. |
| Orchestration simulation | Should | M | Collaboration planning | Deterministic task/delegation/conflict/aggregation plan with no dispatch. |
| Human decision history design | Should | M | Governance review | Redaction, retention, integrity, and override policy agreed before storage. |
| Execution research | Won't in v4.1 | L | Separate architecture approval | No implementation authorized. |

## Compatibility and safety review

The design introduces no public API or persistence change. Any future issue
must preserve exactly one Page per execution, no skipped stage, persisted
storyboard before image generation, completed quality review before approval,
and human authority over every creative or workflow-changing decision.

## Review status

The v4.1 RC1 implements the approved additive DTO foundations for Registry,
Runtime preparation, Orchestration, Collaboration, Human Review, Governance,
Observability, and Reliability. Version is `4.1.0`. These implementations
remain non-executing and retain all design boundaries; no Agent runtime
execution or orchestration dispatch was added.
