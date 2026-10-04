# Extension Registry Foundation

`V44EnterpriseFoundationService.extension_registry(project_id, context)`
returns immutable manifest, compatibility, registry, and summary DTOs for a
candidate extension identity. The compatibility record explicitly states that
the existing Extension SDK remains unchanged.

The foundation cannot discover remotely, persist a registry, load or execute
an extension, grant a permission, enforce isolation, collect telemetry, or
replace any existing Plugin or Extension SDK contract.
