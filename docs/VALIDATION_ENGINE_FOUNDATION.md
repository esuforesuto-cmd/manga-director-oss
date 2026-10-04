# Validation Engine Foundation

`ValidationEngineFoundation` normalizes declared unit, integration,
compatibility, security, documentation, and package validation evidence into
findings. Evidence must state pass/fail and should include a reference.

It is intentionally not a test runner or CI/CD controller. A declared failed
validation produces a blocking diagnostic; absent evidence is explicit rather
than inferred as success. No remediation, bypass, or workflow mutation exists.
