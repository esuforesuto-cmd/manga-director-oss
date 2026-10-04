"""Additive, read-only unified API surface and descriptor registry."""

from __future__ import annotations

from pydantic import Field

from manga_director.platform.api_gateway import (
    UnifiedApiGatewayFoundation,
    UnifiedApiGatewayRequestDTO,
    UnifiedApiGatewayResponseDTO,
)
from manga_director.platform.foundation import UnifiedContextReferenceDTO
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class UnifiedServiceDescriptorDTO(DirectorModel):
    service_id: str
    module_id: str
    public_surfaces: tuple[str, ...] = ()
    legacy_contract_preserved: bool = True
    service_loaded: bool = False
    service_invoked: bool = False


class UnifiedRegistryReport(DirectorModel):
    services: tuple[UnifiedServiceDescriptorDTO, ...] = ()
    service_count: int = Field(default=0, ge=0)
    runtime_routing_changed: bool = False
    external_discovery_performed: bool = False
    planning_only: bool = True


class UnifiedPlatformRegistry:
    """Records caller-supplied metadata; it is not an executable registry."""

    def __init__(self, descriptors: tuple[UnifiedServiceDescriptorDTO, ...] = ()) -> None:
        self._descriptors = {descriptor.service_id: descriptor for descriptor in descriptors}

    def register(self, descriptor: UnifiedServiceDescriptorDTO) -> None:
        if descriptor.service_id in self._descriptors:
            raise ValueError(f"duplicate unified service descriptor: {descriptor.service_id}")
        self._descriptors[descriptor.service_id] = descriptor

    def report(self) -> UnifiedRegistryReport:
        services = tuple(self._descriptors[key] for key in sorted(self._descriptors))
        return UnifiedRegistryReport(services=services, service_count=len(services))


class UnifiedApiSurfaceRequestDTO(DirectorModel):
    project_id: str
    references: tuple[UnifiedContextReferenceDTO, ...] = ()
    requested_surfaces: tuple[str, ...] = ("python", "cli", "fastapi", "mcp", "web-ui")
    public_api_changed: bool = False


class UnifiedApiSurfaceReport(DirectorModel):
    gateway: UnifiedApiGatewayResponseDTO
    registry: UnifiedRegistryReport
    supported_surfaces: tuple[str, ...]
    legacy_contract_preserved: bool = True
    transport_registered: bool = False
    planning_only: bool = True


class UnifiedApiSurfaceService:
    """Composes a compatible facade preview without changing delivery adapters."""

    def __init__(
        self,
        gateway: UnifiedApiGatewayFoundation | None = None,
        registry: UnifiedPlatformRegistry | None = None,
    ) -> None:
        self._gateway = gateway or UnifiedApiGatewayFoundation()
        self._registry = registry or UnifiedPlatformRegistry(_default_descriptors())

    def preview(
        self, request: UnifiedApiSurfaceRequestDTO, workflow_context: WorkflowContext
    ) -> UnifiedApiSurfaceReport:
        gateway = self._gateway.preview(
            UnifiedApiGatewayRequestDTO(project_id=request.project_id, references=request.references),
            workflow_context,
        )
        return UnifiedApiSurfaceReport(
            gateway=gateway,
            registry=self._registry.report(),
            supported_surfaces=request.requested_surfaces,
        )


def _default_descriptors() -> tuple[UnifiedServiceDescriptorDTO, ...]:
    return (
        UnifiedServiceDescriptorDTO(
            service_id="platform-preview",
            module_id="platform",
            public_surfaces=("python", "cli", "fastapi", "mcp", "web-ui"),
        ),
    )

