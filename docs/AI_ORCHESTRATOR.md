# AI Orchestrator Foundation

The AI Orchestrator Foundation summarizes capability and existing evidence
references for one page. It requires human approval and never generates a plan,
dispatches execution, or mutates the workflow.

```python
from manga_director.production import V60CreativeProductionPlatformFoundationService

report = V60CreativeProductionPlatformFoundationService().ai_orchestrator(
    project_id,
    workflow_context,
)
```

Only supplied story, character, world, and timeline references are reported.
Missing evidence is not inferred, fetched, or generated; the domain
`StateMachine` and human review remain authoritative for every next step.
