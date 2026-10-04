# Intelligence Reliability

v4.6 Iteration 3 adds `IntelligenceReliabilityReport`, an immutable reliability
and summary projection over the Intelligence Dashboard.

Health checks, failure detection, monitoring, alerting, retry, and recovery are
explicitly disabled. The report does not change a workflow, persist reliability
state, call an external service, or perform a production operation.
