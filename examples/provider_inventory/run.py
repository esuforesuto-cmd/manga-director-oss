"""Inspect Provider metadata, capability, health, and diagnostic priority."""

from manga_director.adapters import LLMProviderRuntime
from manga_director.production import ProviderManagement


def main() -> None:
    report = ProviderManagement(LLMProviderRuntime()).inventory(refresh=True)
    print(report.to_markdown())


if __name__ == "__main__":
    main()
