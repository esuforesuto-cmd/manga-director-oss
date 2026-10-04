# Data Exchange

## Design contract

Data Exchange will describe envelopes for human-reviewed external exchange.
Each envelope should carry a schema reference, data classification, source
provenance, intended consumer, scope, retention expectation, and approval
boundary.

## Safety boundaries

The design allows metadata validation and Markdown/JSON reporting only. It
does not serialize a Project for external delivery, persist an exchange record,
transform data, import external data, or create a transport connection.

Workflow state remains independent from an exchange proposal. A data envelope
cannot create multiple Pages, skip a stage, generate an image, or approve a
Page.
