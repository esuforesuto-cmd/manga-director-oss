# v3.1.0 Knowledge Evolution Guide

Knowledge Evolution exposes version, snapshot, diff, timeline, analytics,
reliability, and governance DTOs derived through the existing Repository
interface. Values remain bounded and redacted for diagnostics.

The v3.1 layer does not add a mutable Knowledge store, perform a merge, alter
repository contents, call an external service, or change workflow behavior.
Use reports to inform a human decision, then apply any approved change through
the established Project and workflow boundaries.
