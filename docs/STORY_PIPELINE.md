# Story and Character Pipeline

The v5.6 Story Pipeline is a read-only consistency checkpoint for exactly one
existing Page. It reads caller-supplied `story_context` and `timeline_context`
evidence, then reports whether the page is ready for human production review.
It does not rewrite story content, change character data, or advance workflow
state.

The paired Character Pipeline uses `character_context` and `world_context`
evidence to surface continuity prerequisites. Missing evidence is reported as a
finding; it is never inferred, replaced, or persisted by the pipeline.

## Standard

1. Keep the Page scope at one.
2. Reuse approved story, character, world, and timeline context by reference.
3. Record missing continuity evidence before building a prompt.
4. Delegate every state transition to the existing domain StateMachine.

This compact context contract reduces duplicate prompt content without removing
any approved story or character constraint.
