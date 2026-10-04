"""Read-only intelligence for caller-supplied unified creative context."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.platform.foundation import UnifiedCreativeContextDTO
from manga_director.production.director import DirectorModel


class UnifiedContextCoverageDTO(DirectorModel):
    expected_domains: tuple[str, ...] = ("workspace", "knowledge", "agent", "production")
    supplied_domains: tuple[str, ...] = ()
    missing_domains: tuple[str, ...] = ()
    coverage_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    source_loaded: bool = False


class UnifiedContextFindingDTO(DirectorModel):
    finding_id: str
    severity: Literal["info", "advisory"] = "info"
    message: str
    automatic_remediation: bool = False


class UnifiedContextIntelligenceReport(DirectorModel):
    context: UnifiedCreativeContextDTO
    coverage: UnifiedContextCoverageDTO
    findings: tuple[UnifiedContextFindingDTO, ...] = ()
    recommendation: str
    context_mutated: bool = False
    planning_only: bool = True


class UnifiedContextIntelligenceService:
    """Analyzes supplied references without querying or changing their owners."""

    def report(self, context: UnifiedCreativeContextDTO) -> UnifiedContextIntelligenceReport:
        expected = ("workspace", "knowledge", "agent", "production")
        supplied = tuple(reference.domain for reference in context.references)
        missing = tuple(domain for domain in expected if domain not in supplied)
        coverage = UnifiedContextCoverageDTO(
            supplied_domains=supplied,
            missing_domains=missing,
            coverage_ratio=len(supplied) / len(expected),
        )
        findings = tuple(
            UnifiedContextFindingDTO(
                finding_id=f"missing-context:{domain}",
                severity="advisory",
                message=f"Supply an explicit {domain} context reference for a fuller preview.",
            )
            for domain in missing
        )
        recommendation = (
            "All supported context domains are explicitly referenced."
            if not missing
            else "Add only caller-supplied references for the listed context domains."
        )
        return UnifiedContextIntelligenceReport(
            context=context,
            coverage=coverage,
            findings=findings,
            recommendation=recommendation,
        )

