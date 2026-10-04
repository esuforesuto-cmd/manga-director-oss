# Knowledge Index

Knowledge Index projects bounded project identifiers, titles, counts, and
metadata key names through the existing Repository interface. It does not
persist an index, reveal metadata values, contact a remote service, or modify a
Project. Search and summaries are advisory DTOs only.

```python
report = director_planning_service.knowledge_foundation()
```

An empty repository produces an `empty` report with zero references. The index
does not create placeholder entries, write repository records, or alter the
workflow.
