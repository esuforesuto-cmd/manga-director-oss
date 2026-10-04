# Image Backend Management

`BackendManagement` composes the existing `ImageBackendRuntime` into a safe
inventory containing backend metadata, capabilities, preset inventory, local
construction health, and workflow compatibility evidence. It does not generate
an image or alter the ImageGenerator Factory.

Workflow compatibility is metadata validation only. A backend that declares a
workflow format is checked against that declared format; a backend without
workflow metadata is reported as compatible with an explicit informational
message. This is not a workflow execution guarantee.

Use `record_health()` to persist a bounded backend health snapshot via the
Repository port.
