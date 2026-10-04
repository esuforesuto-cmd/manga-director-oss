# Unified SDK Guide

`UnifiedSDKFoundation` is the optional developer-facing entry point for
platform, context-intelligence, runtime-orchestration, and dashboard previews.
It delegates to the same read-only services exposed directly by
`manga_director.platform`.

Use the SDK when an application already has an existing `WorkflowContext` and
wants to compose caller-supplied context references. It is not a replacement
for WorkflowEngine, Repository, Provider, Backend, Plugin, or Extension SDK
APIs and cannot execute a workflow or approve a Page.

