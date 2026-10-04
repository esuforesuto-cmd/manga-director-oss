# Event Processing Intelligence

Event Processing Intelligence is intentionally diagnostic rather than an event
processor. It identifies whether a requested local event record is known and
shows its provenance, correlation metadata, and the Event Bus Foundation's
non-delivery status.

It has no handlers, subscribers, queue, scheduling, dispatch, retry, replay,
persistence, or network transport. An event remains caller-supplied evidence
for a human automation review and never advances a workflow.
