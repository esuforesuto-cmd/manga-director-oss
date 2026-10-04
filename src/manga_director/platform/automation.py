"""v5.2 rule-based automation foundations without automation execution.

All services operate on caller-supplied local metadata. They never dispatch an
event, schedule work, invoke a provider or agent, alter a workflow, persist a
plan, or approve a Page. The StateMachine remains the transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel


class WorkflowTemplateDTO(DirectorModel):
    """A single-Page workflow shape that can be reviewed but never started."""

    template_id: str
    title: str
    owner: str
    page_reference: str
    page_count: Literal[1] = 1
    required_evidence: tuple[str, ...] = ()
    human_review_required: bool = True
    workflow_started: bool = False
    workflow_mutated: bool = False


class WorkflowTemplateReport(DirectorModel):
    template: WorkflowTemplateDTO
    valid: bool
    missing_evidence: tuple[str, ...] = ()
    state_machine_authoritative: bool = True
    planning_only: bool = True


class WorkflowTemplateFoundation:
    """Validates supplied evidence requirements without changing a workflow."""

    def validate(
        self, template: WorkflowTemplateDTO, evidence_types: tuple[str, ...] = ()
    ) -> WorkflowTemplateReport:
        missing = tuple(
            evidence_type
            for evidence_type in template.required_evidence
            if evidence_type not in evidence_types
        )
        return WorkflowTemplateReport(
            template=template,
            valid=not missing
            and template.human_review_required
            and not template.workflow_started
            and not template.workflow_mutated,
            missing_evidence=tuple(sorted(set(missing))),
        )


class AutomationRuleDTO(DirectorModel):
    """A deterministic, human-owned eligibility rule with no action semantics."""

    rule_id: str
    title: str
    owner: str
    required_evidence: tuple[str, ...] = ()
    compatibility: str = ">=5.0,<6.0"
    human_review_required: bool = True
    execution_enabled: bool = False
    self_learning_enabled: bool = False
    automatic_approval_enabled: bool = False


class RuleEvaluationReport(DirectorModel):
    rule: AutomationRuleDTO
    eligible: bool
    missing_evidence: tuple[str, ...] = ()
    explanation: str
    autonomous_decision_made: bool = False
    execution_performed: bool = False
    planning_only: bool = True


class RuleEngineFoundation:
    """Evaluates explicit evidence keys deterministically and side-effect free."""

    def evaluate(
        self, rule: AutomationRuleDTO, evidence_types: tuple[str, ...] = ()
    ) -> RuleEvaluationReport:
        missing = tuple(
            evidence_type for evidence_type in rule.required_evidence if evidence_type not in evidence_types
        )
        safe = (
            rule.human_review_required
            and not rule.execution_enabled
            and not rule.self_learning_enabled
            and not rule.automatic_approval_enabled
        )
        eligible = safe and not missing
        explanation = (
            "rule is eligible for human review"
            if eligible
            else "rule requires evidence or violates a non-execution safety boundary"
        )
        return RuleEvaluationReport(
            rule=rule,
            eligible=eligible,
            missing_evidence=tuple(sorted(set(missing))),
            explanation=explanation,
        )


class AutomationEventDTO(DirectorModel):
    """Immutable caller-supplied event evidence; it is not dispatched."""

    event_id: str
    event_type: str
    producer: str
    page_reference: str
    provenance: str
    correlation_id: str | None = None
    dispatched: bool = False
    persisted: bool = False


class EventBusReport(DirectorModel):
    events: tuple[AutomationEventDTO, ...] = ()
    event_count: int = Field(default=0, ge=0)
    dispatch_started: bool = False
    queue_created: bool = False
    retry_scheduled: bool = False
    planning_only: bool = True


class EventBusFoundation:
    """Stores local metadata references only; it has no delivery semantics."""

    def __init__(self, events: tuple[AutomationEventDTO, ...] = ()) -> None:
        self._events = {event.event_id: event for event in events}
        if len(self._events) != len(events):
            raise ValueError("duplicate automation event")

    def register(self, event: AutomationEventDTO) -> None:
        if event.event_id in self._events:
            raise ValueError(f"duplicate automation event: {event.event_id}")
        self._events[event.event_id] = event

    def report(self) -> EventBusReport:
        events = tuple(self._events[key] for key in sorted(self._events))
        return EventBusReport(events=events, event_count=len(events))


class AutomationRegistryReport(DirectorModel):
    templates: tuple[WorkflowTemplateDTO, ...] = ()
    rules: tuple[AutomationRuleDTO, ...] = ()
    template_count: int = Field(default=0, ge=0)
    rule_count: int = Field(default=0, ge=0)
    external_discovery_performed: bool = False
    runtime_changed: bool = False
    planning_only: bool = True


class AutomationRegistryFoundation:
    """Local template/rule registry that never dynamically discovers a source."""

    def __init__(
        self,
        templates: tuple[WorkflowTemplateDTO, ...] = (),
        rules: tuple[AutomationRuleDTO, ...] = (),
    ) -> None:
        self._templates = {template.template_id: template for template in templates}
        self._rules = {rule.rule_id: rule for rule in rules}
        if len(self._templates) != len(templates) or len(self._rules) != len(rules):
            raise ValueError("duplicate automation registry descriptor")

    def register_template(self, template: WorkflowTemplateDTO) -> None:
        if template.template_id in self._templates:
            raise ValueError(f"duplicate workflow template: {template.template_id}")
        self._templates[template.template_id] = template

    def register_rule(self, rule: AutomationRuleDTO) -> None:
        if rule.rule_id in self._rules:
            raise ValueError(f"duplicate automation rule: {rule.rule_id}")
        self._rules[rule.rule_id] = rule

    def report(self) -> AutomationRegistryReport:
        templates = tuple(self._templates[key] for key in sorted(self._templates))
        rules = tuple(self._rules[key] for key in sorted(self._rules))
        return AutomationRegistryReport(
            templates=templates,
            rules=rules,
            template_count=len(templates),
            rule_count=len(rules),
        )


class AutomationRequestDTO(DirectorModel):
    template_id: str
    rule_id: str
    event_id: str
    evidence_types: tuple[str, ...] = ()
    approval_boundary: str | None = None


class AutomationPlanDTO(DirectorModel):
    automation_id: str
    page_reference: str
    template_id: str
    rule_id: str
    event_id: str
    eligible_for_human_review: bool
    approval_boundary: str | None
    execution_requested: bool = False
    execution_performed: bool = False
    workflow_mutated: bool = False


class AutomationEngineReport(DirectorModel):
    registry: AutomationRegistryReport
    event_bus: EventBusReport
    template: WorkflowTemplateReport | None
    rule: RuleEvaluationReport | None
    plan: AutomationPlanDTO | None
    findings: tuple[str, ...] = ()
    human_review_required: bool = True
    state_machine_authoritative: bool = True
    planning_only: bool = True


class AutomationEngineFoundation:
    """Builds an advisory automation plan from local metadata only."""

    def __init__(
        self,
        registry: AutomationRegistryFoundation | None = None,
        event_bus: EventBusFoundation | None = None,
        templates: WorkflowTemplateFoundation | None = None,
        rules: RuleEngineFoundation | None = None,
    ) -> None:
        self._registry = registry or AutomationRegistryFoundation()
        self._event_bus = event_bus or EventBusFoundation()
        self._templates = templates or WorkflowTemplateFoundation()
        self._rules = rules or RuleEngineFoundation()

    def preview(self, request: AutomationRequestDTO) -> AutomationEngineReport:
        registry = self._registry.report()
        events = self._event_bus.report()
        template = next((item for item in registry.templates if item.template_id == request.template_id), None)
        rule = next((item for item in registry.rules if item.rule_id == request.rule_id), None)
        event = next((item for item in events.events if item.event_id == request.event_id), None)
        findings: list[str] = []
        if template is None:
            findings.append("unknown workflow template")
        if rule is None:
            findings.append("unknown automation rule")
        if event is None:
            findings.append("unknown automation event")
        template_report = self._templates.validate(template, request.evidence_types) if template else None
        rule_report = self._rules.evaluate(rule, request.evidence_types) if rule else None
        if template_report and not template_report.valid:
            findings.extend(template_report.missing_evidence)
        if rule_report and not rule_report.eligible:
            findings.extend(rule_report.missing_evidence or ("rule is not eligible",))
        if request.approval_boundary is None:
            findings.append("human approval boundary is required")
        if event and template and event.page_reference != template.page_reference:
            findings.append("event and template page references differ")
        eligible = not findings and template_report is not None and rule_report is not None
        plan = None
        if template and rule and event:
            plan = AutomationPlanDTO(
                automation_id=f"automation:{template.template_id}:{rule.rule_id}:{event.event_id}",
                page_reference=template.page_reference,
                template_id=template.template_id,
                rule_id=rule.rule_id,
                event_id=event.event_id,
                eligible_for_human_review=eligible,
                approval_boundary=request.approval_boundary,
            )
        return AutomationEngineReport(
            registry=registry,
            event_bus=events,
            template=template_report,
            rule=rule_report,
            plan=plan,
            findings=tuple(sorted(set(findings))),
        )
