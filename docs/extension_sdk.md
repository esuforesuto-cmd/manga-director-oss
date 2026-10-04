# Extension SDK

The public `manga_director.sdk` package provides base classes, immutable context,
manifest validation, local loading, and ZIP packaging. Extensions must not call
Domain internals or alter StateMachine legality.
