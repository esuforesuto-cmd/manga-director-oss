# Repository compatibility

Database repositories preserve `load`, `save`, `exists`, `delete`, and `list`.
The canonical Project aggregate is serialized atomically as JSON; Project,
Chapter, and Page rows additionally expose queryable ownership and page state.
`LocalFileRepository` remains supported without conversion.
