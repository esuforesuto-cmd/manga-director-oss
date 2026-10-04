"""v5.1 declarative composition foundations without runtime activation.

The registry, packs, profiles, templates, and engine process only supplied
metadata.  They never load extensions, invoke services, mutate configuration,
or alter the domain workflow.  The StateMachine remains authoritative.
"""

from __future__ import annotations

from pydantic import Field

from manga_director.production.director import DirectorModel


class CapabilityDescriptorDTO(DirectorModel):
    """A local description of an existing public capability contract."""

    capability_id: str
    title: str
    owner_module: str
    public_surfaces: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    compatibility: str = ">=5.0,<6.0"
    public_contract_preserved: bool = True
    dynamically_loaded: bool = False
    service_invoked: bool = False


class CapabilityRegistryReport(DirectorModel):
    capabilities: tuple[CapabilityDescriptorDTO, ...] = ()
    capability_count: int = Field(default=0, ge=0)
    external_discovery_performed: bool = False
    runtime_changed: bool = False
    planning_only: bool = True


class CapabilityRegistryFoundation:
    """Local, caller-controlled metadata registry; never a plugin loader."""

    def __init__(self, capabilities: tuple[CapabilityDescriptorDTO, ...] = ()) -> None:
        supplied = capabilities or _default_capabilities()
        self._capabilities = {capability.capability_id: capability for capability in supplied}
        if len(self._capabilities) != len(supplied):
            raise ValueError("duplicate capability descriptor")

    def register(self, capability: CapabilityDescriptorDTO) -> None:
        if capability.capability_id in self._capabilities:
            raise ValueError(f"duplicate capability descriptor: {capability.capability_id}")
        self._capabilities[capability.capability_id] = capability

    def report(self) -> CapabilityRegistryReport:
        capabilities = tuple(self._capabilities[key] for key in sorted(self._capabilities))
        return CapabilityRegistryReport(capabilities=capabilities, capability_count=len(capabilities))


class FeaturePackDTO(DirectorModel):
    """A non-executable collection of capability identifiers."""

    pack_id: str
    title: str
    capability_ids: tuple[str, ...]
    compatibility: str = ">=5.0,<6.0"
    executable: bool = False
    installation_required: bool = False


class FeaturePackReport(DirectorModel):
    pack: FeaturePackDTO
    resolved_capability_ids: tuple[str, ...] = ()
    missing_capability_ids: tuple[str, ...] = ()
    valid: bool = False
    services_invoked: bool = False
    planning_only: bool = True


class FeaturePackFoundation:
    """Validates pack references against local registry metadata."""

    def validate(
        self, pack: FeaturePackDTO, registry: CapabilityRegistryFoundation
    ) -> FeaturePackReport:
        available = {item.capability_id for item in registry.report().capabilities}
        duplicates = _duplicates(pack.capability_ids)
        missing = tuple(capability_id for capability_id in pack.capability_ids if capability_id not in available)
        valid = not duplicates and not missing and not pack.executable and not pack.installation_required
        return FeaturePackReport(
            pack=pack,
            resolved_capability_ids=tuple(
                capability_id for capability_id in pack.capability_ids if capability_id in available
            ),
            missing_capability_ids=tuple(sorted(set(missing) | set(duplicates))),
            valid=valid,
        )


class PlatformProfileDTO(DirectorModel):
    """A declarative intended composition with a v5.0 legacy fallback."""

    profile_id: str
    title: str
    feature_pack_ids: tuple[str, ...] = ()
    capability_ids: tuple[str, ...] = ()
    compatibility: str = ">=5.0,<6.0"
    legacy_only_fallback: bool = True
    configuration_changed: bool = False
    execution_routed: bool = False


class PlatformProfileReport(DirectorModel):
    profile: PlatformProfileDTO
    selected_capability_ids: tuple[str, ...] = ()
    missing_feature_pack_ids: tuple[str, ...] = ()
    missing_capability_ids: tuple[str, ...] = ()
    valid: bool = False
    planning_only: bool = True


class PlatformProfileFoundation:
    """Resolves supplied profile references without configuring any service."""

    def validate(
        self,
        profile: PlatformProfileDTO,
        packs: tuple[FeaturePackDTO, ...],
        registry: CapabilityRegistryFoundation,
    ) -> PlatformProfileReport:
        pack_by_id = {pack.pack_id: pack for pack in packs}
        missing_packs = tuple(
            pack_id for pack_id in profile.feature_pack_ids if pack_id not in pack_by_id
        )
        selected = list(profile.capability_ids)
        for pack_id in profile.feature_pack_ids:
            if pack := pack_by_id.get(pack_id):
                selected.extend(pack.capability_ids)
        available = {item.capability_id for item in registry.report().capabilities}
        missing_capabilities = tuple(
            capability_id for capability_id in selected if capability_id not in available
        )
        duplicates = _duplicates(tuple(selected))
        valid = (
            not missing_packs
            and not missing_capabilities
            and not duplicates
            and profile.legacy_only_fallback
            and not profile.configuration_changed
            and not profile.execution_routed
        )
        return PlatformProfileReport(
            profile=profile,
            selected_capability_ids=tuple(sorted(set(selected))),
            missing_feature_pack_ids=tuple(sorted(set(missing_packs))),
            missing_capability_ids=tuple(sorted(set(missing_capabilities) | set(duplicates))),
            valid=valid,
        )


class SolutionTemplateDTO(DirectorModel):
    """A human-reviewed advisory composition blueprint."""

    template_id: str
    title: str
    profile_id: str
    required_evidence: tuple[str, ...] = ()
    human_review_required: bool = True
    creates_project: bool = False
    workflow_started: bool = False
    approval_automated: bool = False


class SolutionTemplateReport(DirectorModel):
    template: SolutionTemplateDTO
    profile_found: bool
    valid: bool
    advisory_only: bool = True
    planning_only: bool = True


class SolutionTemplateFoundation:
    """Checks supplied template metadata while retaining human ownership."""

    def validate(
        self, template: SolutionTemplateDTO, profile: PlatformProfileDTO
    ) -> SolutionTemplateReport:
        profile_found = template.profile_id == profile.profile_id
        valid = (
            profile_found
            and template.human_review_required
            and not template.creates_project
            and not template.workflow_started
            and not template.approval_automated
        )
        return SolutionTemplateReport(template=template, profile_found=profile_found, valid=valid)


class ModuleCompositionRequestDTO(DirectorModel):
    profile: PlatformProfileDTO
    feature_packs: tuple[FeaturePackDTO, ...] = ()
    templates: tuple[SolutionTemplateDTO, ...] = ()


class ModuleCompositionSummary(DirectorModel):
    capability_count: int = Field(default=0, ge=0)
    feature_pack_count: int = Field(default=0, ge=0)
    template_count: int = Field(default=0, ge=0)
    valid: bool = False
    state_machine_authoritative: bool = True
    workflow_mutated: bool = False
    services_invoked: bool = False


class ModuleCompositionReport(DirectorModel):
    registry: CapabilityRegistryReport
    feature_packs: tuple[FeaturePackReport, ...]
    profile: PlatformProfileReport
    templates: tuple[SolutionTemplateReport, ...]
    summary: ModuleCompositionSummary
    planning_only: bool = True


class ModuleCompositionEngineFoundation:
    """Composes supplied metadata into a read-only planning report."""

    def __init__(
        self,
        registry: CapabilityRegistryFoundation | None = None,
        pack_foundation: FeaturePackFoundation | None = None,
        profile_foundation: PlatformProfileFoundation | None = None,
        template_foundation: SolutionTemplateFoundation | None = None,
    ) -> None:
        self._registry = registry or CapabilityRegistryFoundation()
        self._packs = pack_foundation or FeaturePackFoundation()
        self._profiles = profile_foundation or PlatformProfileFoundation()
        self._templates = template_foundation or SolutionTemplateFoundation()

    def preview(self, request: ModuleCompositionRequestDTO) -> ModuleCompositionReport:
        pack_reports = tuple(
            self._packs.validate(pack, self._registry) for pack in request.feature_packs
        )
        profile = self._profiles.validate(request.profile, request.feature_packs, self._registry)
        templates = tuple(
            self._templates.validate(template, request.profile) for template in request.templates
        )
        valid = profile.valid and all(report.valid for report in pack_reports) and all(
            report.valid for report in templates
        )
        return ModuleCompositionReport(
            registry=self._registry.report(),
            feature_packs=pack_reports,
            profile=profile,
            templates=templates,
            summary=ModuleCompositionSummary(
                capability_count=len(profile.selected_capability_ids),
                feature_pack_count=len(pack_reports),
                template_count=len(templates),
                valid=valid,
            ),
        )


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if values.count(value) > 1}))


def _default_capabilities() -> tuple[CapabilityDescriptorDTO, ...]:
    return (
        CapabilityDescriptorDTO(
            capability_id="platform.unified-context",
            title="Unified Creative Context",
            owner_module="platform",
            public_surfaces=("python", "sdk"),
        ),
        CapabilityDescriptorDTO(
            capability_id="platform.unified-api",
            title="Unified Creative API",
            owner_module="platform",
            public_surfaces=("python", "cli", "fastapi", "mcp", "web-ui", "sdk"),
            requires=("platform.unified-context",),
        ),
        CapabilityDescriptorDTO(
            capability_id="platform.unified-runtime",
            title="Unified Runtime",
            owner_module="runtime",
            public_surfaces=("python", "sdk"),
        ),
        CapabilityDescriptorDTO(
            capability_id="platform.unified-sdk",
            title="Unified SDK",
            owner_module="sdk",
            public_surfaces=("python",),
            requires=("platform.unified-api", "platform.unified-runtime"),
        ),
        CapabilityDescriptorDTO(
            capability_id="enterprise.governance",
            title="Enterprise Governance",
            owner_module="enterprise",
            public_surfaces=("python", "cli", "fastapi", "mcp", "web-ui"),
        ),
        CapabilityDescriptorDTO(
            capability_id="extensions.manifest",
            title="Extension Manifest",
            owner_module="extensions",
            public_surfaces=("python", "sdk"),
        ),
    )
