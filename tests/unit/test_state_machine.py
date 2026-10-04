import pytest

from manga_director.domain.exceptions import InvalidPageTransition
from manga_director.domain.state_machine import PageState, StateMachine


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        (PageState.DRAFT, PageState.DESIGNED),
        (PageState.DESIGNED, PageState.REVIEWED),
        (PageState.REVIEWED, PageState.STORYBOARDED),
        (PageState.STORYBOARDED, PageState.PROMPT_BUILT),
        (PageState.PROMPT_BUILT, PageState.GENERATED),
        (PageState.GENERATED, PageState.QUALITY_CHECKED),
        (PageState.QUALITY_CHECKED, PageState.APPROVED),
    ],
)
def test_next_state_follows_the_fixed_workflow(current: PageState, expected: PageState) -> None:
    machine = StateMachine()

    assert machine.next_state(current) == expected
    machine.validate_transition(current, expected)


def test_terminal_approved_state_has_no_successor() -> None:
    with pytest.raises(InvalidPageTransition):
        StateMachine().next_state(PageState.APPROVED)


def test_invalid_state_transition_is_rejected() -> None:
    with pytest.raises(InvalidPageTransition):
        StateMachine().validate_transition(PageState.DRAFT, PageState.GENERATED)
