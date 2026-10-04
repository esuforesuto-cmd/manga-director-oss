"""Inspect a redacted Enterprise configuration snapshot."""

from pathlib import Path

from manga_director.cli.config import configuration_snapshot, load_config

if __name__ == "__main__":
    config = load_config(Path("config.yaml"), profile="enterprise")
    print(configuration_snapshot(config).model_dump_json(indent=2))
