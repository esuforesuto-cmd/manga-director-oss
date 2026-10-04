"""A support-agent plugin that preserves the page state machine."""

from manga_director.plugins import PluginRegistry, PluginType
from manga_director.workflow import AgentResult, WorkflowContext


class ToneCheckAgent:
    def execute(self, context: WorkflowContext) -> AgentResult:
        return AgentResult(
            success=True,
            state=context.state,
            payload={"tone_check": "advisory"},
            events=[],
            messages=["Tone check completed."],
        )


class SampleAgentPlugin:
    name = "sample-agent"
    version = "1.0.0"
    description = "Adds a support-only tone check agent."

    def initialize(self) -> None:
        pass

    def register(self, registry: PluginRegistry) -> None:
        registry.register(
            PluginType.AGENT,
            "tone-check",
            ToneCheckAgent,
            plugin_name=self.name,
            metadata={"role": "support", "command": "tone-check"},
        )

    def shutdown(self) -> None:
        pass
