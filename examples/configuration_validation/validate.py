"""Report safe schema and integrity information for a configuration."""

from manga_director.cli.config import AppConfig, configuration_governance

print(configuration_governance(AppConfig(profile="enterprise", read_only=True)).model_dump())
