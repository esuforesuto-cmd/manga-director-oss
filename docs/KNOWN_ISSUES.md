# v5.6 RC1 Known Issues

No known critical defect was found in the focused v5.6 Engine contracts or the
one-page integration validation.

## Release limitations

- The Engine reports are advisory; they do not create print, Web, eBook,
  package, metadata, bundle, or archive files.
- A comparable v5.5 pipeline benchmark is not available in this workspace.
- Hosted CI, external CVE lookup, signing, GitHub pre-release publication, and
  PyPI upload remain maintainer-controlled release gates; they are not local
  Engine defects.

# v5.7 RC1 Known Issues

No known critical defect has been identified in the focused v5.7 Production
Platform contracts. The Platform reports are intentionally advisory and do not
perform automation, scheduling, Plugin lifecycle, event publication, snapshot
restore, workflow transition, approval, export, or repository persistence.

## Release limitations

- A performance comparison against a v5.6 Platform projection is unavailable:
  v5.7 is the first optional Platform-level projection. The RC records a
  one-page report benchmark and retains v5.6 workflow regression contracts.
- Protected CI, external CVE lookup, signing, GitHub pre-release publication,
  and PyPI upload are maintainer-controlled release gates.
- The local `pip --target` install smoke did not complete in this workspace.
  Wheel metadata, contents, zip-import behavior, and dependency checking pass;
  a clean maintainer environment must complete the installation smoke before
  public RC publication.

# v6.0 RC1 Known Issues

No known critical defect has been identified in the local v6.0 Platform Kernel
contracts. The new reports remain advisory and do not execute a workflow,
automatically approve a Page, load extensions, publish marketplace content,
enforce policy, or emit telemetry.

## Release limitations

- A historical v5.7-to-v6.0 performance baseline is not stored in a common
  benchmark format; RC1 records a local provider-free bounded measurement.
- Protected CI, external CVE lookup, signing, GitHub pre-release publication,
  and PyPI upload require maintainer authority.

# v6.0 Final Known Issues

No known critical defect was identified in the final local Platform Kernel,
SDK, Extension, Marketplace, Governance, Observability, AI Orchestrator, or
v5.x compatibility contracts.

## Release limitations

- The v6.0 performance measurement is a local baseline; no common historical
  v5.7-to-v6.0 benchmark format exists for a cross-version claim.
- Protected CI, external CVE lookup, signing, tag creation, GitHub publication,
  and PyPI upload remain maintainer-controlled release controls.
