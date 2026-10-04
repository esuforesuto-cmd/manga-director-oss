# Cross-Agent Knowledge Sharing

v4.6 Iteration 2 adds `CrossAgentKnowledgeSharingReport`, an immutable review
projection over the Cross-Agent Memory foundation. It records that provenance,
consent, and redaction are required before a human could consider sharing.

`V46IntelligenceService.knowledge_sharing()` does not share knowledge, read or
write memory, message an Agent, synchronize state, grant access, transfer
ownership, or call an external service. The report is a local, exactly-one-page
evidence model only.
