# Repository Scalability

`RepositoryScalability` is an optional read-side helper built only on `ProjectRepository`. It adds compact project, chapter, page, metadata, and snapshot indexes; bounded history pagination; and batch-oriented project scans. The repository protocol and existing callers remain unchanged.

Indexes are in-process and explicitly invalidated after a controlled write or reload. They are diagnostics and convenience indexes, not a replacement for the persisted project aggregate.
