# Creative Pipeline Design Example (v4.2)

The v4.2 pipeline is a checkpointed, non-executable plan, not a production runner.

```text
Story plan -> Manga plan -> Asset evidence -> Review packet -> Publishing checklist
```

The Manga plan may recommend at most one legal Page action. The existing
StateMachine remains authoritative for all transitions. The plan cannot create
an image, finish a quality review, approve a Page, publish, notify, or write a
repository.

See [Creative Pipeline](../../docs/CREATIVE_PIPELINE.md) and the
[Pipeline Test Plan](../../docs/PIPELINE_TEST_PLAN.md).
