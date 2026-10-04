"""Smoke benchmark for passive long-running stability contract validation."""

from __future__ import annotations

from release_validation import _service

from manga_director.workflow import WorkflowContext


def run() -> bool:
    return _service().reliability_report(WorkflowContext(page={"id": "one"})).long_running.valid


if __name__ == "__main__":
    print(f"long_running_validation_valid={run()}")
