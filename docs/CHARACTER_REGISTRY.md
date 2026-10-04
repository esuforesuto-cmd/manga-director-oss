# Character Registry

Character Registry is a read-only projection of the supplied
`character_registry` mapping. The current `character_context.id` identifies the
active character, and the report remains scoped to exactly one existing Page.

The engine does not create, rename, delete, or persist character records. When
registry evidence is absent, it reports the gap for a human editor to resolve.
