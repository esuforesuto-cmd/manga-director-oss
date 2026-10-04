"""Measure local v5.1 composition-maturity reporting without runtime actions."""

from timeit import timeit

from manga_director.platform import (
    CompositionPlatformMaturityService,
    FeaturePackDTO,
    ModuleCompositionRequestDTO,
    PlatformProfileDTO,
    SolutionTemplateDTO,
)


def _request() -> ModuleCompositionRequestDTO:
    pack = FeaturePackDTO(
        pack_id="creative-planning",
        title="Creative Planning",
        capability_ids=("platform.unified-context", "platform.unified-api"),
    )
    profile = PlatformProfileDTO(
        profile_id="local.creative-review",
        title="Creative Review",
        feature_pack_ids=(pack.pack_id,),
        capability_ids=("platform.unified-sdk",),
    )
    template = SolutionTemplateDTO(
        template_id="story-to-review",
        title="Story to Review",
        profile_id=profile.profile_id,
        required_evidence=("storyboard", "quality-review"),
    )
    return ModuleCompositionRequestDTO(
        profile=profile, feature_packs=(pack,), templates=(template,)
    )


def main() -> None:
    service = CompositionPlatformMaturityService()
    request = _request()
    elapsed = timeit(lambda: service.report(request), number=1_000)
    print(f"composition-platform-v5.1 projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
