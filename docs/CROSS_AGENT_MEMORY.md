# Cross-Agent Memory Foundation

v4.6 Iteration 1 adds `CrossAgentMemoryReport` with immutable memory-reference,
consent, and summary DTOs. It models an attributable memory reference for human
review without creating a shared mutable memory store.

`V46IntelligenceFoundationService.cross_agent_memory()` returns a local report
whose default boundary is strict: no memory read, write, synchronization,
automatic retrieval, access grant, agent communication, ownership transfer, or
external access is performed.

The report marks provenance, consent, and redaction as required. Future work
must keep those requirements explicit and cannot treat a memory reference as
authority to execute a workflow or approve content.
