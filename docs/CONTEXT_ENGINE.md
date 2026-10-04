# Context Engine

## v6.0 Iteration 2 foundation

The Context Engine projects the supplied `WorkflowContext` metadata into a
compact context inventory. It recognizes story, character, world, timeline,
production, and review context keys and reports whether the minimum creative
context is available.

It never persists context, expands prompts, loads external records, executes
an AI request, or changes the Page state. The service first validates the
existing one-page v5.7 evidence, preserving storyboard and quality-review
requirements.

```python
from manga_director.production import V60CreativeProductionPlatformIntelligenceService

report = V60CreativeProductionPlatformIntelligenceService().context_engine(
    "volume-1",
    workflow_context,
)
```

`report.complete` is `True` only when story, character, world, and timeline
context inputs are supplied. Missing inputs are reported as incomplete; the
engine does not infer, load, or create them.

## Compatibility

This is an opt-in Application-layer report. No existing context, API, workflow,
repository, or delivery contract changes.
