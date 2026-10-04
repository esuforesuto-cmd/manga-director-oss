"""Outer-layer helpers that apply active plugin contributions to application composition."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, cast

from manga_director.adapters.factory import ImageGeneratorFactory
from manga_director.adapters.image_generator import ImageGenerator
from manga_director.adapters.llm_factory import LLMFactory
from manga_director.adapters.llm_provider import LLMProvider
from manga_director.domain.exceptions import PluginRegistrationError
from manga_director.domain.state_machine import PageState
from manga_director.plugins.contracts import PluginType
from manga_director.plugins.registry import PluginRegistry
from manga_director.workflow import Agent


def apply_image_generator_plugins(registry: PluginRegistry) -> None:
    """Expose registered image-generator builders through the existing factory."""
    for contribution in registry.list(PluginType.IMAGE_GENERATOR):
        if not callable(contribution.value):
            raise PluginRegistrationError(
                f"Image generator contribution '{contribution.name}' must be a callable builder."
            )
        ImageGeneratorFactory.register(
            contribution.name, cast(Callable[..., ImageGenerator], contribution.value)
        )


def apply_llm_plugins(registry: PluginRegistry) -> None:
    """Expose registered LLM builders through the provider-neutral LLM factory."""
    for contribution in registry.list(PluginType.LLM):
        if not callable(contribution.value):
            raise PluginRegistrationError(
                f"LLM contribution '{contribution.name}' must be a callable builder."
            )
        LLMFactory.register(contribution.name, cast(Callable[..., LLMProvider], contribution.value))


def apply_agent_plugins(
    registry: PluginRegistry,
    primary: Mapping[PageState, Agent],
    support: Mapping[str, Agent],
) -> tuple[dict[PageState, Agent], dict[str, Agent]]:
    """Add explicitly declared plugin agents without changing page transition rules.

    Plugin agents are support agents by default. A primary-agent replacement
    requires both a valid existing state and explicit ``replace: true`` metadata;
    the existing page state machine still validates its result.
    """
    primary_agents = dict(primary)
    support_agents = dict(support)
    for contribution in registry.list(PluginType.AGENT):
        agent = _agent_value(contribution.value, contribution.name)
        role = str(contribution.metadata.get("role", "support"))
        if role == "support":
            command = str(contribution.metadata.get("command", contribution.name))
            if command in support_agents:
                raise PluginRegistrationError(
                    f"Support agent command '{command}' is already registered."
                )
            support_agents[command] = agent
            continue
        if role != "primary":
            raise PluginRegistrationError(
                f"Agent contribution '{contribution.name}' has unsupported role '{role}'."
            )
        if contribution.metadata.get("replace") is not True:
            raise PluginRegistrationError(
                f"Primary agent contribution '{contribution.name}' must explicitly set replace: true."
            )
        raw_state = contribution.metadata.get("state")
        try:
            state = PageState(str(raw_state))
        except ValueError as exc:
            raise PluginRegistrationError(
                f"Primary agent contribution '{contribution.name}' requires a valid page state."
            ) from exc
        primary_agents[state] = agent
    return primary_agents, support_agents


def _agent_value(value: Any, name: str) -> Agent:
    agent = value() if callable(value) else value
    if not hasattr(agent, "execute"):
        raise PluginRegistrationError(f"Agent contribution '{name}' must provide execute(context).")
    return cast(Agent, agent)
