# v6.x SDK Compatibility Matrix

| SDK surface | v5.x contract | v6.x LTS status | Maintenance rule |
| --- | --- | --- | --- |
| Python | Preserved | Supported | Keep imports and DTO behavior additive. |
| CLI | Preserved | Supported | Do not change commands or execution semantics. |
| FastAPI / REST | Preserved | Supported | Keep endpoint and OpenAPI compatibility. |
| MCP | Preserved | Supported | Keep protocol and server-info compatibility. |
| Web UI | Preserved | Supported | Keep existing consumer contracts available. |

`SDKCapabilityDTO` is a read-only compatibility descriptor. It does not
generate, publish, register, or replace an SDK surface.
