"""Load the built-in offline profile without changing Core behavior."""

from pathlib import Path

from manga_director.cli.config import configuration_snapshot, load_config

if __name__ == "__main__":
    config = load_config(Path("config.yaml"), profile="offline")
    print(configuration_snapshot(config).model_dump_json(indent=2))
