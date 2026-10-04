# Automation Lifecycle Management

Automation Lifecycle Management records an advisory automation reference and
whether its human approval boundary is declared. Its only stage is `advisory`;
it does not transition, persist, retain, archive, restore, resume, or recover
an automation.

This preserves the existing workflow lifecycle and StateMachine as the source
of truth while providing an explicit management DTO for future human-operated
processes.
