"""Trusted LocalFile construction for the private D05 pre-provider boundary."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.production.future_durable_generation_attempt import (
    _LocalFutureGenerationAttemptStore,
)
from manga_director.production.future_durable_generation_boundary import (
    DurableGenerationBoundaryReport,
    ProviderDispatchRequestV1,
    ProviderInvocationPermitV1,
    _DurableGenerationBoundaryCore,
)
from manga_director.production.future_generation_admission_contract import (
    GenerationAdmissionManifestV1,
    PromptEvidenceV1,
    ProviderRequestBindingV1,
    SnapshotIdentityV1,
    StoryboardEvidenceV1,
)
from manga_director.production.future_generation_admission_evaluator import (
    GenerationAdmissionCurrentEvidence,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.page_execution_fence import WindowsPageExecutionFence

_PROVIDER_BINDING_KEY = "future_generation_provider_binding"
_TARGET_REFERENCE_KEY = "future_generation_target_reference"


class LocalFileDurableGenerationBoundary:
    """The sole trusted D05 construction path; it has no provider capability."""

    def __init__(self, repository: LocalFileRepository) -> None:
        self._repository = repository
        self._state_machine = StateMachine()
        self._core = _DurableGenerationBoundaryCore(
            _LocalFutureGenerationAttemptStore(_attempt_owner_root(repository)),
            _LocalFileCurrentAdmissionEvidenceReader(repository, self._state_machine),
            WindowsPageExecutionFence,
        )

    def reserve(self, manifest: GenerationAdmissionManifestV1) -> DurableGenerationBoundaryReport:
        return self._core.reserve(manifest)

    def prepare_provider_start(self, manifest: GenerationAdmissionManifestV1) -> DurableGenerationBoundaryReport:
        return self._core.prepare_provider_start(manifest)

    def reopen(self, manifest: GenerationAdmissionManifestV1) -> DurableGenerationBoundaryReport:
        return self._core.reopen(manifest)

    def permit_is_current(
        self, manifest: GenerationAdmissionManifestV1, permit: ProviderInvocationPermitV1
    ) -> bool:
        return self._core.permit_is_current(manifest, permit)

    def consume_for_dispatch(
        self, manifest: GenerationAdmissionManifestV1, permit: ProviderInvocationPermitV1
    ) -> ProviderDispatchRequestV1 | None:
        """Return a private dispatch request only after D05 one-time consumption."""

        return self._core.consume_for_dispatch(manifest, permit)


class _LocalFileCurrentAdmissionEvidenceReader:
    """Read D02/D03 evidence only from the current revisioned LocalFile page."""

    def __init__(self, repository: LocalFileRepository, state_machine: StateMachine) -> None:
        self._repository = repository
        self._state_machine = state_machine

    def read(self, manifest: GenerationAdmissionManifestV1) -> GenerationAdmissionCurrentEvidence:
        snapshot = self._repository._load_revisioned(manifest.project_id)
        page_number = _page_number(manifest.page_id)
        page = snapshot.project.page(page_number)
        self._state_machine.validate_transition(PageState.PROMPT_BUILT, PageState.GENERATED)
        storyboard = StoryboardEvidenceV1.model_validate(page.storyboard)
        prompt = PromptEvidenceV1.model_validate(page.prompt)
        binding = ProviderRequestBindingV1.model_validate(page.metadata.get(_PROVIDER_BINDING_KEY))
        target = page.metadata.get(_TARGET_REFERENCE_KEY)
        if not isinstance(target, str):
            raise ValueError("authoritative generation target is unavailable")
        return GenerationAdmissionCurrentEvidence(
            project_id=snapshot.project.id,
            page_id=str(page.page_number),
            execution_target_reference=target,
            workflow_state=page.state.value,
            snapshot=SnapshotIdentityV1(revision=snapshot.revision, fingerprint=snapshot.fingerprint),
            storyboard=storyboard,
            prompt=prompt,
            provider_request=binding,
            attempt_id=manifest.attempt_id,
        )


def _attempt_owner_root(repository: LocalFileRepository) -> Path:
    """Derive an isolated root from the LocalFile durability owner, never a caller path."""

    root = repository._root
    if not root.is_absolute():
        raise ValueError("trusted LocalFile durability root is unavailable")
    return root.resolve() / "_durability" / "_future_durable_generation" / "attempts"


def _page_number(page_id: str) -> int:
    if not isinstance(page_id, str) or not page_id.isdigit() or int(page_id) < 1:
        raise ValueError("authoritative page identity is unavailable")
    return int(page_id)
