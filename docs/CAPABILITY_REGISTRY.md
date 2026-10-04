# Capability Registry

## Purpose

The Capability Registry is a local, declarative catalogue of supported v5.0
capability contracts. It is neither a dynamic extension registry nor a runtime
dependency resolver.

## Proposed descriptor

| Field | Meaning |
| --- | --- |
| `capability_id` | Stable namespaced identifier, never inferred from an import path. |
| `title` / `description` | Human-readable purpose and non-goals. |
| `owner` | Existing module responsible for behavior and data. |
| `surface` | Supported Python, CLI, REST, MCP, Web UI, or SDK exposure. |
| `compatibility` | Declared v5.0 LTS and future supported ranges. |
| `requires` | Other declarative capability identifiers. |
| `evidence_requirements` | Required provenance, review, and quality inputs. |
| `workflow_constraints` | StateMachine rules that remain applicable. |

## Rules

- Metadata is supplied or bundled locally; remote discovery and installation
  are out of scope.
- A descriptor cannot own a Project, Page, Repository, or workflow transition.
- Cycles, missing requirements, unknown versions, and incompatible ranges are
  validation findings, not instructions to load or execute anything.
- The registry never removes a legacy API.

## Families

Platform (context/API/runtime/SDK), Creative (workspace/review), Knowledge,
Production, Enterprise, and Extension metadata are candidate families. Future
implementation must provide deterministic validation, legacy fixtures,
extension isolation checks, and workflow-invariant tests.
