# Unified API Gateway Foundation

`UnifiedApiGatewayFoundation` is an in-process, transport-neutral preview
facade. It accepts an explicit request DTO and existing `WorkflowContext`, then
delegates to the Unified Platform Foundation service.

It does not add HTTP routes, alter OpenAPI, replace REST/FastAPI/MCP/CLI
contracts, dispatch a request, persist a response, or mutate a workflow. This
keeps v4.8 delivery APIs fully compatible while establishing a testable future
gateway seam.

