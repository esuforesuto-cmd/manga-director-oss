"""Inspect configuration governance before admitting an application runtime."""

from manga_director.cli.config import AppConfig, configuration_governance


def main() -> None:
    report = configuration_governance(AppConfig())
    print(report.model_dump_json(indent=2))
    if not (report.compatible and report.integrity_valid):
        raise SystemExit("Configuration is not ready for startup.")


if __name__ == "__main__":
    main()
