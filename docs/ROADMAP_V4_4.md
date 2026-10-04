# v4.4 Roadmap: Enterprise Creative Platform

## Must

| ID | Issue | Purpose / background | Priority | Scope | Estimate | Layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V44-WS-01 | Enterprise Workspace vocabulary | Establish compatible workspace, owner, session, snapshot, and health terminology over v4.3 evidence. | P0 | Workspace | M | Application | v4.3 Project and Workflow contracts |
| V44-COL-01 | Collaboration context and review planning | Make role, handoff, review, and decision prerequisites visible without changing authority. | P0 | Collaboration | M | Application | V44-WS-01, StateMachine invariants |
| V44-PORT-01 | Portfolio inventory and health planning | Aggregate caller-supplied, redacted project evidence for enterprise visibility. | P0 | Portfolio | M | Application | v4.3 operations/quality evidence |
| V44-EXT-01 | Extension manifest and compatibility planning | Define capability, provenance, isolation, and SDK compatibility records. | P0 | Extensions | M | Application / Extension boundary | Existing Extension SDK |
| V44-MKT-01 | Workflow Marketplace catalog and policy design | Define a local, non-executing catalog admission model. | P0 | Marketplace | M | Application | V44-EXT-01, workflow contracts |

## Should

| ID | Issue | Purpose / background | Priority | Scope | Estimate | Layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V44-WS-02 | Workspace timeline and activity report | Present supplied workspace activity without persistence or notifications. | P1 | Workspace | S | Application | V44-WS-01 |
| V44-COL-02 | Collaboration readiness and decision trace | Explain human review prerequisites and unresolved handoffs. | P1 | Collaboration | M | Application | V44-COL-01, QA evidence |
| V44-PORT-02 | Portfolio risk and delivery-confidence report | Provide diagnostic-only portfolio observations. | P1 | Portfolio | M | Application | V44-PORT-01 |
| V44-EXT-02 | Extension governance and isolation report | Provide human-review evidence before any opt-in activation work. | P1 | Extensions | M | Application / Extension boundary | V44-EXT-01 |
| V44-MKT-02 | Marketplace provenance and license report | Make candidate source and license review deterministic. | P1 | Marketplace | S | Application | V44-MKT-01 |

## Could

| ID | Issue | Purpose / background | Priority | Scope | Estimate | Layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V44-PORT-03 | Portfolio trend visualization DTO | Compare caller-provided portfolio snapshots without retaining history. | P2 | Portfolio | S | Application | V44-PORT-02 |
| V44-MKT-03 | Workflow template compatibility matrix | Describe compatibility across existing workflow profiles. | P2 | Marketplace | M | Application | V44-MKT-01, v4.3 profiles |
| V44-EXT-03 | Extension lifecycle recommendation | Explain manually supplied lifecycle evidence without enforcement. | P2 | Extensions | S | Application | V44-EXT-02 |

## Won't

| Item | Reason |
| --- | --- |
| Marketplace download, installation, publishing, payment, or billing | Requires a separate security, commercial, and service architecture. |
| Cloud tenancy, identity, remote collaboration, or distributed runtime | Outside the local-first v4.4 planning scope. |
| Automatic task allocation, approval, workflow execution, or multi-page generation | Violates human governance and the canonical StateMachine boundaries. |
| Core, Repository, Workflow Engine, or Extension SDK redesign | Would break the required v4.3 compatibility baseline. |
