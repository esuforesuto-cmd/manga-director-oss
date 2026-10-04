# Platform Profile Foundation

`PlatformProfileDTO` declares an intended set of Feature Packs and direct
capabilities. `PlatformProfileFoundation` resolves only caller-supplied
metadata and requires a `legacy_only_fallback`.

A valid profile must have known packs and capabilities, no duplicates, no
configuration change, and no execution routing. The profile report therefore
supports composition previews without selecting a Provider, Backend, Agent, or
workflow.

Profiles are optional metadata. Omitting a profile preserves exactly the v5.0
LTS integration path.
