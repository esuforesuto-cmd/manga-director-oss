from __future__ import annotations

import stat
from collections.abc import Callable
from types import SimpleNamespace

import pytest

from manga_director.production import (
    future_durable_generation_attempt,
    future_real_delivery_binding_authority,
    next_generation_generation_evidence_persistence,
)


class _LstatProbe:
    def __init__(self, *, error: OSError | None = None) -> None:
        self.calls = 0
        self._error = error

    def lstat(self) -> object:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return SimpleNamespace(st_mode=stat.S_IFREG | 0o600)


@pytest.mark.parametrize(
    "guard",
    (
        future_durable_generation_attempt._is_link_or_reparse_point,
        future_real_delivery_binding_authority._is_reparse_point,
        next_generation_generation_evidence_persistence._is_link_or_reparse_point,
    ),
)
def test_stat_guards_use_one_lstat_and_tolerate_missing_windows_attributes(
    guard: Callable[[object], bool],
) -> None:
    path = _LstatProbe()

    assert guard(path) is False
    assert path.calls == 1


@pytest.mark.parametrize(
    "guard",
    (
        future_durable_generation_attempt._is_link_or_reparse_point,
        future_real_delivery_binding_authority._is_reparse_point,
        next_generation_generation_evidence_persistence._is_link_or_reparse_point,
    ),
)
def test_stat_guards_preserve_oserror_as_false(guard: Callable[[object], bool]) -> None:
    path = _LstatProbe(error=PermissionError("private path detail"))

    assert guard(path) is False
    assert path.calls == 1
