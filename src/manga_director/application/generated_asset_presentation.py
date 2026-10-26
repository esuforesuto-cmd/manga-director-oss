"""Transport-neutral private use case for safe local generated-asset presentation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, cast

from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_page_output_proof import (
    PageOutputProofUnavailable,
    PageOutputResolverPort,
)
from manga_director.production.next_generation_safe_local_generated_asset_presentation import (
    SafeLocalGeneratedAssetPresentationError,
    SafeLocalGeneratedAssetPresenter,
)
from manga_director.repositories.local_file import LocalFileRepository

_PRESENTABLE_STATES = {
    PageState.GENERATED,
    PageState.QUALITY_CHECKED,
    PageState.APPROVED,
}


class GeneratedAssetPresentationUnavailable(ValueError):
    """Redacted application failure for a missing or unsafe presentation."""


@dataclass(slots=True)
class GeneratedAssetPresentation:
    """Verified response bytes and their retained exact-file release capability."""

    image_bytes: bytes = field(repr=False)
    _release: Any = field(repr=False)

    def release(self) -> None:
        self._release()


class GeneratedAssetPresentationService:
    """Resolve one authoritative Page and delegate its logical asset to production."""

    def __init__(
        self,
        repository: LocalFileRepository,
        presenter: SafeLocalGeneratedAssetPresenter,
        page_output_resolver: PageOutputResolverPort | None = None,
    ) -> None:
        self._repository = repository
        self._presenter = presenter
        self._page_output_resolver = page_output_resolver

    def get(self, project_id: str, page_number: int) -> GeneratedAssetPresentation:
        try:
            page = self._repository._load_authoritative_page(project_id, page_number)
            image = page.image
            if (
                page.state not in _PRESENTABLE_STATES
                or not isinstance(image, Mapping)
                or set(image) != {"artifact_kind", "output_asset_id"}
                or image.get("artifact_kind") != "logical_output_asset"
            ):
                raise GeneratedAssetPresentationUnavailable(
                    "generated asset presentation is unavailable"
                )
            output_asset_id = image.get("output_asset_id")
            if not isinstance(output_asset_id, str):
                raise GeneratedAssetPresentationUnavailable(
                    "generated asset presentation is unavailable"
                )
            if self._page_output_resolver is not None:
                resolved = self._page_output_resolver.resolve(
                    project_id, str(page_number), output_asset_id
                )
                return GeneratedAssetPresentation(
                    resolved.image_bytes,
                    resolved.release,
                )
            presentation = self._presenter.present(
                project_id, str(page_number), output_asset_id
            )
            return GeneratedAssetPresentation(
                presentation.image_bytes,
                presentation.release,
            )
        except GeneratedAssetPresentationUnavailable:
            raise
        except SafeLocalGeneratedAssetPresentationError as error:
            raise GeneratedAssetPresentationUnavailable(
                "generated asset presentation is unavailable"
            ) from error
        except PageOutputProofUnavailable as error:
            raise GeneratedAssetPresentationUnavailable(
                "generated asset presentation is unavailable"
            ) from error
        except Exception as error:
            raise GeneratedAssetPresentationUnavailable(
                "generated asset presentation is unavailable"
            ) from error


def build_generated_asset_presentation(
    repository: LocalFileRepository,
    *,
    page_output_resolver: PageOutputResolverPort | None = None,
) -> GeneratedAssetPresentationService:
    """Compose fixed private roots without opening or creating them."""

    normal_root = repository._next_generation_normal_execution_owner_root()
    presenter = SafeLocalGeneratedAssetPresenter(
        ledger_root=repository._workflow_application_ledger_owner_root(),
        evidence_root=normal_root / "evidence",
        asset_root=normal_root / "assets",
    )
    return GeneratedAssetPresentationService(
        repository, presenter, page_output_resolver
    )


def attach_generated_asset_presentation(
    application: object,
    service: GeneratedAssetPresentationService,
) -> None:
    """Attach one private capability without changing the public application signature."""

    cast(Any, application)._generated_asset_presentation = service


def generated_asset_presentation_for(
    application: object,
) -> GeneratedAssetPresentationService | None:
    service = getattr(application, "_generated_asset_presentation", None)
    return service if isinstance(service, GeneratedAssetPresentationService) else None
