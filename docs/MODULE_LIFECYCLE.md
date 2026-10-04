# Module Lifecycle Management

`ModuleLifecycleManagementService` lists registry capabilities as `declared`
module lifecycle references. Every reference retains its owner module and
public-contract flag.

The report never transfers ownership, persists lifecycle state, enforces
retention, archives content, deletes data, restores modules, or invokes
recovery. Existing Project, Page, Repository, and Workflow lifecycles stay the
only authoritative lifecycles.
