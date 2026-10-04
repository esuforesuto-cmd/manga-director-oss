# Resource Manager

`V57ProductionWorkspaceService.resources()` validates caller-supplied,
one-Page capacity references. It reports insufficient or out-of-scope resource
IDs without allocating staff, changing permissions, scheduling work, or
persisting an allocation.

When no allocation is supplied, it reports a single human-owner reference for
diagnostic use only.
