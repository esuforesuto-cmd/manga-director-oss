# Reliability

The v2.2 Iteration 3 reliability boundary is intentionally conservative:
Workflow execution is exactly one Page step, StateMachine validation remains
authoritative, and Approval remains an explicit post-quality action.

Reliability evidence includes Project integrity checks, transactional/atomic
Repository behavior, persisted Batch checkpoints, bounded notification retry,
Plugin/Extension failure isolation, health DTOs, diagnostic documents, and
provider-free repeatability benchmarks.

The repeatability benchmarks report relative timing spread rather than enforcing
a throughput SLO across different CI machines. A wide regression guard catches
pathological instability while maintaining deterministic, credential-free CI.

No distributed recovery, asynchronous EventBus, cloud monitoring, real-time
dashboard, new Workflow, Provider, Plugin, or Database is introduced here.

## v2.4 Iteration 3 reliability operations

The optional `manga_director.production` reliability facade composes existing
Workflow, Repository, and Observability ports into read-only resume validation,
workflow-consistency checks, Repository integrity scans, recovery simulations,
long-running stability summaries, and production-readiness reports. It never
executes an Agent, transitions a Page, alters the StateMachine, or persists a
recovery action.

See [Recovery Guide](RECOVERY_GUIDE.md), [Long-Running Operations](LONG_RUNNING_OPERATIONS.md),
[Production Checklist](PRODUCTION_CHECKLIST.md), and
[Diagnostics Reference](DIAGNOSTICS_REFERENCE.md).

## v4.1 multi-agent reliability foundation

The v4.1 assurance facade exposes Retry Policy, Timeout Policy, Recovery,
Failure Report, and Reliability Summary DTOs for one-page collaborative plans.
They describe safe human-operated boundaries only: automatic retry attempts are
zero, timeout/cancellation enforcement is disabled, and recovery/remediation is
never started or persisted.

The facade does not execute an agent, change workflow state, mutate the
Repository, retain long-term memory, or bypass storyboard and quality-review
approval gates.
