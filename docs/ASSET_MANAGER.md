# Asset Manager Foundation

`V57ProductionPlatformFoundationService.assets()` projects artifact and
metadata keys as observed asset-lifecycle evidence for the current one-Page
context. Each record is descriptive only and identifies its source as an
existing artifact or metadata key.

The service does not create, version, archive, distribute, alter, or persist
assets. Existing Asset DTOs and Repository interfaces remain canonical.

## Asset identity

Observed asset identity includes both `source_kind` and `source_key`. An
Artifact key and Metadata key with the same name remain separate evidence,
preserving provenance without changing either source.

## Compatibility

Callers may omit this optional report without changing v5.x asset behavior.
