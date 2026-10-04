# Execution Policy

`ExecutionPolicy` is a typed policy boundary owned by the Batch layer.

| Policy | v1 behavior |
| --- | --- |
| `SequentialExecution` | Implemented. Executes one Queue item at a time in planner order. |
| `ParallelExecution` | API placeholder only. No threads, processes, queues, or network workers are started. |
| `AutoExecution` | API placeholder only. It does not select or launch a policy. |

The Batch engine rejects non-sequential policies with a `WorkflowError` rather
than silently changing execution semantics. Future parallel implementations
must retain per-Page state validation, durable Queue ownership, explicit human
approval, and no duplicate Page execution.
