# Knowledge Core v1

Knowledge Core provides a deterministic, provenance-bearing reference view for
story, character, world, asset, production, and review evidence. References
are sorted by `knowledge_id`, and duplicate identifiers are rejected before a
report is returned.

```python
from manga_director.production import (
    KnowledgeCoreReferenceDTO,
    V60CreativeProductionPlatformFoundationService,
)

report = V60CreativeProductionPlatformFoundationService().knowledge_core(
    (
        KnowledgeCoreReferenceDTO(
            knowledge_id="story:volume-1",
            project_id="volume-1",
            kind="story",
            source_reference="story_context",
            provenance="workflow-metadata",
        ),
    )
)
```

The service neither builds nor persists a graph, changes repositories, nor
replaces knowledge owners. It is an additive diagnostic boundary; workflow
transitions remain governed by the domain `StateMachine`.
