# Capability Registry Foundation

`CapabilityRegistryFoundation` is an in-memory, local catalogue of supplied
`CapabilityDescriptorDTO` values. A descriptor records an existing capability's
identifier, owner, public surfaces, dependencies, compatibility range, and
read-only safety flags.

The registry sorts descriptors deterministically and rejects duplicate IDs. It
does not discover remote extensions, import code, load plugins, invoke a
service, or change the v5.0 LTS public API.

```python
from manga_director.platform import CapabilityRegistryFoundation

report = CapabilityRegistryFoundation().report()
assert report.external_discovery_performed is False
assert report.runtime_changed is False
```

Registry metadata is advisory. Existing module owners retain behavior and
source-of-truth ownership.
