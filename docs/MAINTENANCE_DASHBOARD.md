# Maintenance Dashboard

`MaintenanceDashboardDTO` composes lifecycle, upgrade, health, deprecation, and maintenance-registry analysis into a presentation-neutral response. It is exposed through the optional `UnifiedSDKFoundation.lifecycle_dashboard` method.

The dashboard identifies a readiness state for a human maintenance decision. It cannot perform upgrades, phase changes, deprecations, monitoring, runtime recovery, workflow actions, or approvals.
