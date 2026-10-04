"""A metadata-only repository contribution for a future repository port."""

from manga_director.plugins import PluginRegistry, PluginType


class SampleRepositoryPlugin:
    name = "sample-repository"
    version = "1.0.0"
    description = "Declares a future repository adapter contribution."

    def initialize(self) -> None:
        pass

    def register(self, registry: PluginRegistry) -> None:
        registry.register(
            PluginType.REPOSITORY,
            "sample-repository",
            {"driver": "sample"},
            plugin_name=self.name,
        )

    def shutdown(self) -> None:
        pass
