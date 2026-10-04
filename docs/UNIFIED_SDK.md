# Unified SDK

## Purpose

The Unified SDK is a typed convenience layer for consumers that want a single
entry point to compose existing services. It is deliberately narrower than the
full application surface and does not replace existing SDK, Plugin, or
Extension contracts.

## Proposed SDK capabilities

- Construct validated, immutable unified context and evidence envelopes.
- Discover declared local module descriptors supplied explicitly by callers.
- Compose read-only platform, project, and decision summaries.
- Serialize existing-compatible DTOs for Python, CLI, REST, MCP, and Web UI
  adapters.
- Provide migration helpers that call current public interfaces unchanged.

## Prohibited SDK capabilities

- Direct StateMachine transition, workflow execution, or Page mutation.
- Image generation, approval, automatic recommendation acceptance, or Agent
  dispatch.
- Persistence, service routing, policy enforcement, Cloud synchronization,
  marketplace operation, billing, or distributed execution.

## Compatibility policy

The SDK is opt-in. It exposes explicit adapters rather than aliases that
silently alter behavior, and must preserve the original error semantics and
DTOs when delegating to an existing public service. Existing extension points
remain supported and are not required to adopt a unified SDK dependency.

