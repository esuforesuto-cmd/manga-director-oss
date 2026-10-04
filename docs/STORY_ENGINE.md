# Story Engine v1

Story Engine v1 is a read-only Story Workflow Standard for exactly one existing
Page. It combines story, character, world, timeline, foreshadowing, conflict,
and ending evidence into an immutable report for human creative review.

It does not write story content, revise a character, change world settings,
resolve a foreshadowing thread, approve a Page, or alter the domain workflow.

## Standard workflow

1. Plan from supplied story and world evidence.
2. Validate story structure, character motivation, and ordered timeline events.
3. Record the chapter goal for the one-Page scope.
4. Trace declared foreshadow setups and payoffs.
5. Review conflict evidence against character motivation and world constraints.
6. Confirm the ending goal and foreshadowing hand-off before human review.

`V56StoryEngineService.story_engine()` is transport-neutral and advisory only.
Existing APIs, repository contracts, StateMachine behavior, and delivery adapters
remain unchanged.
