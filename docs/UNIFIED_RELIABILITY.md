# Unified Reliability

`UnifiedReliabilityService` reports Context, API, Runtime, SDK, and Dashboard
components as `not_checked` unless an existing owner provides independent
evidence. This makes missing health evidence explicit and avoids an inaccurate
claim of operational health.

It cannot execute a health check, change runtime configuration, classify a
failure, retry, recover, or repair a component.

