# Chapter Planner

Chapter Planner projects the current Page into a chapter reference and declared
chapter goal. Its scope is fixed to exactly one Page; it cannot schedule,
generate, merge, or transition Pages.

Use `chapter_id` metadata and `story_context.chapter_goal` to preserve chapter
intent across the existing workflow. Actual workflow progression continues to be
validated solely by the domain StateMachine.
