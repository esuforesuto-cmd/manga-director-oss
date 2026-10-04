from __future__ import annotations

from enum import StrEnum

from manga_director.domain.exceptions import InvalidPageTransition


class PageState(StrEnum):
    DRAFT = "Draft"
    DESIGNED = "Designed"
    REVIEWED = "Reviewed"
    STORYBOARDED = "Storyboarded"
    PROMPT_BUILT = "PromptBuilt"
    GENERATED = "Generated"
    QUALITY_CHECKED = "QualityChecked"
    APPROVED = "Approved"


class StateMachine:
    """The single authority for forward-only manga page state transitions."""

    _next_states: dict[PageState, PageState] = {
        PageState.DRAFT: PageState.DESIGNED,
        PageState.DESIGNED: PageState.REVIEWED,
        PageState.REVIEWED: PageState.STORYBOARDED,
        PageState.STORYBOARDED: PageState.PROMPT_BUILT,
        PageState.PROMPT_BUILT: PageState.GENERATED,
        PageState.GENERATED: PageState.QUALITY_CHECKED,
        PageState.QUALITY_CHECKED: PageState.APPROVED,
    }
    _commands: dict[PageState, str] = {
        PageState.DESIGNED: "design",
        PageState.REVIEWED: "review",
        PageState.STORYBOARDED: "storyboard",
        PageState.PROMPT_BUILT: "prompt",
        PageState.GENERATED: "generate",
        PageState.QUALITY_CHECKED: "quality",
        PageState.APPROVED: "approve",
    }

    def validate_transition(self, current_state: PageState, next_state: PageState) -> None:
        """Raise when `next_state` is not the one allowed successor."""
        allowed = self._next_states.get(current_state)
        if allowed != next_state:
            expected = allowed.value if allowed else "no successor (terminal state)"
            raise InvalidPageTransition(
                f"Cannot transition from {current_state.value} to {next_state.value}; "
                f"expected {expected}."
            )

    def next_state(self, current_state: PageState) -> PageState:
        """Return the single legal successor or raise for the terminal state."""
        try:
            return self._next_states[current_state]
        except KeyError as exc:
            raise InvalidPageTransition(
                f"{current_state.value} is terminal and has no next state."
            ) from exc

    def command_for(self, next_state: PageState) -> str:
        return self._commands[next_state]

    def next_command(self, current_state: PageState) -> str:
        return self.command_for(self.next_state(current_state))

    def validate_command(self, current_state: PageState, command: str) -> PageState:
        next_state = self.next_state(current_state)
        expected_command = self.command_for(next_state)
        if command != expected_command:
            raise InvalidPageTransition(
                f"'{command}' cannot run from {current_state.value}; "
                f"the executable step is '{expected_command}'."
            )
        return next_state
