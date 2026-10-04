"""Export and validate a safe runtime-configuration snapshot."""

from manga_director.cli.config import AppConfig
from manga_director.production import RuntimeConfiguration


def main() -> None:
    configuration = RuntimeConfiguration(AppConfig(profile="production"))
    exported = configuration.export("yaml")
    print(configuration.report().to_markdown())
    print(configuration.validate_import(exported).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
