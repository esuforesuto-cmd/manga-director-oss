# Plugin Examples

The runnable skeletons in [`examples/plugins`](../../examples/plugins) show one plugin directory per extension. Copy an example directory into the local `plugins/` directory or install it through the CLI.

## Support Agent

`sample_agent` registers an optional `tone-check` support command. It returns the standard `AgentResult`; it does not invoke another agent or alter state.

## Image Provider

`sample_image` registers a `sample-image` builder. After discovery, select it in `config.yaml`:

```yaml
default_image_generator: sample-image
plugin_directory: plugins
```

The provider is resolved through the existing image factory. The ImageAgent remains provider-agnostic.

## Repository and Prompt

`sample_repository` and `sample_prompt` show metadata-only contributions. They are ready for the future repository and prompt-pipeline composition points; they do not replace project persistence or Markdown prompt rendering in the current page runtime.

## Testing a plugin

Test the manifest, lifecycle order, dependency errors, and each contribution's contract. Use a temporary plugin root and `PluginManager` rather than mutating the package's built-in registries globally.
