"""Keep the benchmark harness runnable without asserting unstable performance budgets."""

from benchmarks.smoke import run_smoke


def test_benchmark_smoke_covers_available_provider_free_components() -> None:
    timings = run_smoke()
    assert set(timings) == {
        "workflow",
        "repository",
        "database",
        "prompt",
        "llm",
        "image",
        "notification",
        "batch",
        "platform_kernel",
    }
    assert all(elapsed >= 0.0 for elapsed in timings.values())
