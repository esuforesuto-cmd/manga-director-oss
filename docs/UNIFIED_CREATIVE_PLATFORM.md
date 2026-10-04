# Unified Creative Platform

## Purpose

The platform is a compatibility-first catalogue and composition boundary for
existing capabilities. It makes ownership explicit without creating another
owner for projects, pages, knowledge, agents, assets, policies, or decisions.

## Platform domains

| Domain | Existing owner responsibility | v5 consolidation role |
| --- | --- | --- |
| Workspace | Sessions, participants, activity, and project views. | Supply scope references and dashboards. |
| Knowledge | Graphs, memory, provenance, quality, and lifecycle evidence. | Supply source-linked context and reports. |
| Agents | Profiles, plans, collaboration, review, and governance evidence. | Supply human-reviewed planning evidence. |
| Production | Pipeline, assets, deliverables, quality, and operations evidence. | Supply project production summaries. |
| Enterprise | Portfolio, organization, extension, marketplace, and reliability evidence. | Supply organization-level summaries. |
| Decision | Alternatives, recommendations, review, approval, and trace evidence. | Supply explicit decision packets. |
| Ecosystem | Service, plugin, workflow, exchange, and federation metadata. | Supply declared capability descriptors. |

## Shared platform packet

The proposed packet is a DTO-only envelope containing a `platform_scope`,
`context_references`, `domain_summaries`, `evidence`, `findings`,
`recommendations`, `review_requirements`, and `provenance`. All fields are
optional/additive for transport compatibility and reference existing identifiers
rather than copying owner records.

## Admission rules

- A packet must be constructed from supplied data or existing public services.
- It must identify its source modules and freshness.
- It may describe a recommendation but cannot accept, enforce, or execute it.
- It cannot persist an aggregate, dispatch an Agent, invoke a service, alter a
  workflow, or publish externally.

