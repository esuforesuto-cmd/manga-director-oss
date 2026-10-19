"""Private read-only use case for one approved local PNG download."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, cast

from manga_director.domain.project import Page
from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_safe_local_generated_asset_presentation import (
    SafeLocalGeneratedAssetPresentationError,
    SafeLocalGeneratedAssetPresenter,
)
from manga_director.repositories.local_file import LocalFileRepository

_WORKFLOW_ENTRY_KEYS = {"kind", "from", "to", "step"}


class ApprovedAssetDownloadUnavailable(ValueError):
    """Redacted application failure for unavailable approved bytes."""


@dataclass(slots=True)
class ApprovedAssetDownload:
    """Verified response bytes and their retained exact-file release capability."""

    image_bytes: bytes = field(repr=False)
    _release: Any = field(repr=False)

    def release(self) -> None:
        self._release()


class ApprovedAssetDownloadService:
    """Compose authoritative approval state with the existing exact-file proof."""

    def __init__(
        self,
        repository: LocalFileRepository,
        presenter: SafeLocalGeneratedAssetPresenter,
    ) -> None:
        self._repository = repository
        self._presenter = presenter

    def get(self, project_id: str, page_number: int) -> ApprovedAssetDownload:
        proof = None
        try:
            page = self._repository._load_authoritative_page(project_id, page_number)
            output_asset_id = _approved_output_asset_id(page)
            proof = self._presenter._prove(
                project_id,
                str(page.page_number),
                output_asset_id,
            )
            result = ApprovedAssetDownload(
                image_bytes=proof._lease.image_bytes,
                _release=proof.release,
            )
            proof = None
            return result
        except ApprovedAssetDownloadUnavailable:
            raise
        except SafeLocalGeneratedAssetPresentationError as error:
            raise ApprovedAssetDownloadUnavailable(
                "approved asset download is unavailable"
            ) from error
        except Exception as error:
            raise ApprovedAssetDownloadUnavailable(
                "approved asset download is unavailable"
            ) from error
        finally:
            if proof is not None:
                proof.release()


def _approved_output_asset_id(page: Page) -> str:
    approval = page.approval
    history = page.history
    image = page.image
    if (
        page.state is not PageState.APPROVED
        or not isinstance(approval, Mapping)
        or set(approval) != {"approved_by"}
        or not isinstance(approval.get("approved_by"), str)
        or not cast(str, approval["approved_by"]).strip()
        or not history
        or not all(isinstance(item, Mapping) for item in history)
        or not _is_transition(
            history[-1],
            source="QualityChecked",
            target="Approved",
            step="Approved",
        )
        or sum(
            _is_transition(
                item,
                source="PromptBuilt",
                target="Generated",
                step="Generated",
            )
            for item in history
        )
        != 1
        or not isinstance(image, Mapping)
        or set(image) != {"artifact_kind", "output_asset_id"}
        or image.get("artifact_kind") != "logical_output_asset"
        or not isinstance(image.get("output_asset_id"), str)
    ):
        raise ApprovedAssetDownloadUnavailable(
            "approved asset download is unavailable"
        )
    return cast(str, image["output_asset_id"])


def _is_transition(
    value: object,
    *,
    source: str,
    target: str,
    step: str,
) -> bool:
    return bool(
        isinstance(value, Mapping)
        and set(value) == _WORKFLOW_ENTRY_KEYS
        and value.get("kind") == "workflow"
        and value.get("from") == source
        and value.get("to") == target
        and value.get("step") == step
    )


def build_approved_asset_download(
    repository: LocalFileRepository,
) -> ApprovedAssetDownloadService:
    """Compose fixed private roots without opening or creating them."""

    normal_root = repository._next_generation_normal_execution_owner_root()
    presenter = SafeLocalGeneratedAssetPresenter(
        ledger_root=repository._workflow_application_ledger_owner_root(),
        evidence_root=normal_root / "evidence",
        asset_root=normal_root / "assets",
    )
    return ApprovedAssetDownloadService(repository, presenter)


def attach_approved_asset_download(
    application: object,
    service: ApprovedAssetDownloadService,
) -> None:
    """Attach one private capability without changing the public application signature."""

    cast(Any, application)._approved_asset_download = service


def approved_asset_download_for(
    application: object,
) -> ApprovedAssetDownloadService | None:
    service = getattr(application, "_approved_asset_download", None)
    return service if isinstance(service, ApprovedAssetDownloadService) else None
