# v4.5 Roadmap: Creative Intelligence Ecosystem

## Must

| ID | Issue | Purpose / background | Priority | Scope | Estimate | Layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V45-SVC-01 | Creative Service descriptor model | Establish compatible local identity, capability, provenance, and compatibility terminology. | P0 | Services | M | Application | v4.4 Enterprise Platform contracts |
| V45-PLG-01 | Plugin ecosystem compatibility model | Describe Plugin and Extension SDK capability, isolation, lifecycle, and policy evidence without changing the SDK. | P0 | Plugins / Extensions | M | Application / Extension boundary | Existing Plugin and Extension SDK |
| V45-MKT-01 | Workflow marketplace exchange model | Define local workflow-profile, provenance, license, compatibility, and admission-review evidence. | P0 | Workflow Marketplace | M | Application | v4.4 Marketplace, Workflow contracts |
| V45-KNX-01 | Knowledge exchange descriptor model | Define redacted knowledge schema, traceability, quality, consent, and sharing-readiness evidence. | P0 | Knowledge | M | Knowledge / Application | Existing Knowledge Repository |
| V45-FED-01 | Federation trust and interoperability model | Define trust-domain, handshake, consent, and rollback planning records. | P0 | Federation | M | Application | V45-SVC-01, V45-KNX-01 |

## Should

| ID | Issue | Purpose / background | Priority | Scope | Estimate | Layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V45-SVC-02 | Service compatibility report | Explain supplied capability and policy compatibility for human review. | P1 | Services | S | Application | V45-SVC-01 |
| V45-PLG-02 | Plugin provenance and isolation report | Make human readiness criteria visible before any separately approved activation work. | P1 | Plugins / Extensions | M | Application / Extension boundary | V45-PLG-01 |
| V45-MKT-02 | Workflow exchange policy report | Explain profile compatibility, license, provenance, and StateMachine boundaries. | P1 | Workflow Marketplace | M | Application | V45-MKT-01 |
| V45-KNX-02 | Knowledge sharing quality report | Make redaction, ownership, consent, trace, and quality prerequisites reviewable. | P1 | Knowledge | M | Knowledge / Application | V45-KNX-01 |
| V45-FED-02 | Federation readiness report | Explain trust, consent, compatibility, isolation, and rollback requirements. | P1 | Federation | M | Application | V45-FED-01 |

## Could

| ID | Issue | Purpose / background | Priority | Scope | Estimate | Layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V45-ECO-01 | Ecosystem relationship visualization DTO | Present caller-supplied local relationships without persisting or synchronizing them. | P2 | Ecosystem | S | Application | V45-SVC-01, V45-KNX-01 |
| V45-MKT-03 | Workflow template comparison matrix | Compare supplied workflow-profile metadata without installation or execution. | P2 | Workflow Marketplace | M | Application | V45-MKT-01 |
| V45-KNX-03 | Knowledge exchange recommendation | Explain missing supplied evidence without automatic remediation. | P2 | Knowledge | S | Knowledge / Application | V45-KNX-02 |

## Won't

| Item | Reason |
| --- | --- |
| Remote marketplace, discovery, download, install, publishing, payment, or billing | Requires separate commercial, security, service, and operational architecture. |
| Plugin or extension execution, permission grant, or SDK redesign | Requires explicit isolation and compatibility approval beyond this planning cycle. |
| Knowledge transfer, synchronization, merge, replication, remote search, or ownership change | Requires dedicated privacy, consent, durability, and access-control design. |
| Federation networking, identity, messaging, consensus, distributed scheduling, or Cloud tenancy | Outside local-first v4.5 planning scope. |
| Automatic workflow execution, approval, stage skipping, or multi-page generation | Violates human governance and canonical StateMachine boundaries. |
| Core, Repository, Workflow Engine, Plugin, or Extension SDK redesign | Would break required v4.4 compatibility. |
