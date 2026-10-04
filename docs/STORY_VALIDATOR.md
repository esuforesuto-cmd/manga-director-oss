# Story Validator

Story Validator applies only deterministic evidence checks:

- Story structure requires `story_context.premise` and a chapter goal.
- Character motivation requires `character_context.motivation` or the explicit
  `character_motivation` metadata value.
- Timeline validation requires a non-empty `timeline_context.events` sequence
  with unique ascending integer `sequence` values.

The validator identifies absent or malformed evidence. It does not decide story
quality, alter dialogue, resolve contradictions automatically, or approve a
Page. Human editorial review remains the authority for creative judgment.
