# v5.4 Quality Architecture

## Scope

The proposed Quality Plane is an additive, read-only Application-layer design.
It assembles caller-supplied evidence from Quality, Review, Testing, CI/CD, and
Governance without owning state, storage, execution, or presentation.

```text
Existing workflow / review / test / CI-CD / governance evidence
                              |
                              v
                 Quality evidence normalizer (planned)
                              |
                              v
  Metrics + validation + findings + recommendation DTOs (planned)
                              |
                              v
      Human review / existing StateMachine / existing release process
```

## Planned responsibilities

| Area | Planned responsibility | Explicitly not responsible for |
| --- | --- | --- |
| Quality Framework | Assemble policy, evidence, findings, and recommendation. | Mutating Pages, tests, or workflows. |
| Review Pipeline | Describe required review gates and evidence completeness. | Running reviewers or granting approval. |
| Quality Metrics | Calculate declared metric values from supplied inputs. | Inventing evidence or changing thresholds. |
| Validation Framework | Produce deterministic pass, warn, fail, or unknown findings. | Repairing failures or bypassing checks. |
| Release Governance | Summarize policy, compatibility, security, and sign-off evidence. | Tagging, publishing, signing, or releasing. |

## Ownership and compatibility

Core domain objects, the StateMachine, WorkflowEngine, repositories, Runtime,
and all public surfaces retain their current ownership. The Quality Plane must
be optional, must accept legacy evidence shapes through adapters, and must not
introduce new required configuration or a repository-interface change.

## Integration boundaries

Future adapters may expose reports through Python, CLI, FastAPI, MCP, and Web
UI only as additive query/reporting operations. Adapter validation delegates
Page transition rules to the existing StateMachine. A quality recommendation is
not approval evidence; a completed quality review remains required before a
Page can be approved.

## Security and privacy

Evidence contracts should carry source, timestamp, scope, policy revision, and
redaction classification. Unknown provenance produces an explicit finding.
No secrets, remote CI credentials, or source artifacts are stored by this
design.
