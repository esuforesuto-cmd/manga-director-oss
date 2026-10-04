"""Metadata DTOs for provider and image-backend runtime discovery."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AdapterMetadata(BaseModel):
    """Safe, provider-neutral metadata registered alongside an adapter builder."""

    model_config = ConfigDict(frozen=True)

    name: str
    display_name: str
    priority: int = Field(default=100, ge=0)
    capabilities: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    aliases: dict[str, str] = Field(default_factory=dict)
    workflow_metadata: dict[str, str] = Field(default_factory=dict)
    presets: dict[str, dict[str, str]] = Field(default_factory=dict)


class AdapterHealth(BaseModel):
    """Health evidence limited to local adapter construction, never a network probe."""

    name: str
    healthy: bool
    messages: list[str] = Field(default_factory=list)


class ProviderFallbackPolicy(BaseModel):
    """Declarative fallback policy reserved for a future application-layer executor."""

    model_config = ConfigDict(frozen=True)

    providers: tuple[str, ...] = ()
    enabled: bool = False


class AdapterWarmupReport(BaseModel):
    """Safe local warmup evidence; adapters are constructed but never invoked."""

    kind: str
    ready: bool
    registered: int = Field(ge=0)
    healthy: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)
    messages: list[str] = Field(default_factory=list)
