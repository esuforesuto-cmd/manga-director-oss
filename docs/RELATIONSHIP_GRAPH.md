# Relationship Graph

Relationship Graph reads `character_context.relationships` entries containing a
`target` and a relationship `type`. Every target must exist in the supplied
Character Registry before the graph is ready.

The graph is diagnostic only: it neither changes relationships nor infers a
missing relationship from story text. This preserves established character
dynamics in long-running series.
