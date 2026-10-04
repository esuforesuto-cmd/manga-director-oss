# v6.x Technical Debt Register

| Area | Deferred item | LTS treatment | Exit evidence |
| --- | --- | --- | --- |
| Platform Health | Cross-version benchmark format | Retain the structured v6.0 local baseline manifest; cross-version comparison remains deferred | Comparable maintenance benchmark. |
| SDK | External consumer compatibility telemetry | Keep compatibility matrices review-based with local contract validation | Owner-supplied consumer validation. |
| Extensions | Remote lifecycle certification | Preserve local descriptor-only scope with local contract validation | Deployment-controlled lifecycle audit. |
| Marketplace | Remote signing and publication | Keep certification local and human-gated with local contract validation | Signed owner publication record. |
| Security | External CVE and hosted scanning | Retain deterministic local secret-pattern evidence validation; track external controls as release evidence | Maintainer audit evidence. |
| Operations | Hosted enterprise deployment probes | Retain local deployment guide | Deployment-owned production evidence. |

This register does not authorize implementation work or alter frozen APIs.
