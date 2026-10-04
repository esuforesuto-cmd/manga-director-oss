"""A metadata-only prompt contribution retaining Markdown as the template format."""

from manga_director.plugins import PluginRegistry, PluginType


class SamplePromptPlugin:
    name = "sample-prompt"
    version = "1.0.0"
    description = "Declares a Markdown prompt template contribution."

    def initialize(self) -> None:
        pass

    def register(self, registry: PluginRegistry) -> None:
        registry.register(
            PluginType.PROMPT,
            "sample-markdown",
            {"template": "# Panel\n\n{{ panel_description }}\n", "format": "markdown"},
            plugin_name=self.name,
        )

    def shutdown(self) -> None:
        pass
