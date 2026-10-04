"""Measure local v5.2 automation maturity reporting without runtime actions."""

from timeit import timeit

from manga_director.platform import (
    AutomationEngineFoundation,
    AutomationEventDTO,
    AutomationPlatformMaturityService,
    AutomationRegistryFoundation,
    AutomationRequestDTO,
    AutomationRuleDTO,
    EventBusFoundation,
    WorkflowTemplateDTO,
)


def _service_and_request() -> tuple[AutomationPlatformMaturityService, AutomationRequestDTO]:
    template = WorkflowTemplateDTO(
        template_id="storyboard-review",
        title="Storyboard Review",
        owner="creative-operations",
        page_reference="page-001",
        required_evidence=("storyboard", "quality-review"),
    )
    rule = AutomationRuleDTO(
        rule_id="review-ready",
        title="Review Readiness",
        owner="creative-operations",
        required_evidence=("storyboard", "quality-review"),
    )
    event = AutomationEventDTO(
        event_id="review-completed",
        event_type="quality-review.completed",
        producer="quality-review",
        page_reference="page-001",
        provenance="benchmark",
    )
    engine = AutomationEngineFoundation(
        registry=AutomationRegistryFoundation((template,), (rule,)),
        event_bus=EventBusFoundation((event,)),
    )
    return AutomationPlatformMaturityService(engine), AutomationRequestDTO(
        template_id=template.template_id,
        rule_id=rule.rule_id,
        event_id=event.event_id,
        evidence_types=("storyboard", "quality-review"),
        approval_boundary="editor-review",
    )


def main() -> None:
    service, request = _service_and_request()
    elapsed = timeit(lambda: service.report(request), number=1_000)
    print(f"automation-platform-v5.2 projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
