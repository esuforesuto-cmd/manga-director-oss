# Knowledge Repository

`KnowledgeService` is the supported read-only projection over the existing
`ProjectRepository` port. It creates `KnowledgeSnapshot`, summary, health, and
search reports without introducing a separate persistence model or changing
the repository interface.

```python
from manga_director.production import KnowledgeService

report = KnowledgeService(project_repository).report()
```

Only project identifiers, titles, counts, and sorted metadata keys are exposed.
Metadata values remain in the Project aggregate. The service does not save,
delete, or mutate repository records; workflow transitions remain owned by the
domain `StateMachine`.
