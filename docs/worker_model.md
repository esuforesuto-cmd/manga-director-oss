# Worker Model

The Worker boundary is deliberately narrow:

```python
class Worker(Protocol):
    def run(self, page_context: WorkflowContext) -> WorkflowResult: ...
```

`WorkflowWorker` is the default implementation. It owns one injected
`WorkflowEngine`, invokes `WorkflowEngine.run()` for one Page context, and
returns the final `WorkflowResult`. It has no Agent registry, StateMachine,
Repository, Queue, or provider knowledge.

The Batch engine owns context loading and persistence around the Worker call.
This separates Page execution from Batch scheduling and preserves the existing
Page Workflow unchanged.
