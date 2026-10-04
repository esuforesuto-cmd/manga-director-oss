"""Transport-neutral v5 API gateway foundation.

The gateway is a read-only facade around the unified foundation service. It
does not install HTTP routes, replace public APIs, dispatch work, or mutate a
workflow.
"""

from __future__ import annotations

from manga_director.platform.foundation import (
    UnifiedContextReferenceDTO,
    UnifiedPlatformFoundationReport,
    UnifiedPlatformFoundationService,
)
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class UnifiedApiGatewayRequestDTO(DirectorModel):
    project_id: str
    references: tuple[UnifiedContextReferenceDTO, ...] = ()
    requested_surface: str = "unified-platform-preview"
    legacy_contract_required: bool = True
    request_dispatched: bool = False


class UnifiedApiGatewayResponseDTO(DirectorModel):
    gateway_id: str
    report: UnifiedPlatformFoundationReport
    legacy_contract_preserved: bool = True
    route_registered: bool = False
    response_persisted: bool = False


class UnifiedApiGatewayFoundation:
    """Offers an opt-in, in-process report facade without transport changes."""

    def __init__(self, platform: UnifiedPlatformFoundationService | None = None) -> None:
        self._platform = platform or UnifiedPlatformFoundationService()

    def preview(
        self, request: UnifiedApiGatewayRequestDTO, workflow_context: WorkflowContext
    ) -> UnifiedApiGatewayResponseDTO:
        report = self._platform.report(request.project_id, workflow_context, request.references)
        return UnifiedApiGatewayResponseDTO(
            gateway_id=f"unified-api:{report.context.platform_id}", report=report
        )
