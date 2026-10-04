# Knowledge Search

`KnowledgeService.search()` and
`DirectorFoundationService.knowledge_search()` provide repository-derived,
read-only search results. Queries are normalized for surrounding whitespace and
case; an empty query returns the stable project-reference view.

```python
result = director_foundation_service.knowledge_search("world")
```

Search considers project IDs, titles, and metadata keys only. Metadata values
are never returned, and search does not write to the repository or alter
workflow state.
