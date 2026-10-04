# Marketplace Catalog Foundation

`V44EnterpriseFoundationService.marketplace_catalog(project_id, context)`
returns immutable local catalog, entry, policy, and summary DTOs. Each entry
has an exactly-one-Page scope and requires human review.

This is a catalog vocabulary only. It cannot remotely discover, download,
install, execute, publish, distribute, pay for, bill, or otherwise operate a
workflow marketplace. It cannot bypass the persisted-storyboard,
completed-quality-review, or StateMachine boundaries.
