# v3.3 Migration and Upgrade Strategy

v3.3 planning introduces no runtime feature, persistence format, workflow
behavior, or version change. Projects remain on the v3.2.0 stable baseline
while candidate Issues are reviewed.

When a future v3.3 implementation is proposed, its migration record must:

1. preserve existing Project files, Repository ports, CLI, FastAPI, MCP, and
   Web UI contracts;
2. document any new optional DTO as additive and transport-neutral;
3. prove exactly one Page per workflow execution and StateMachine authority;
4. require a persisted storyboard before generation and completed quality
   review before approval; and
5. include compatibility, rollback, security/redaction, test, documentation,
   and benchmark evidence.

No plan authorizes autonomous AI, implicit persistence, automatic archive or
deletion, publishing, release actions, Cloud services, or distributed runtime.
