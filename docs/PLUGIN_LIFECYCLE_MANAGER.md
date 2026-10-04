# Plugin Lifecycle Manager

The Plugin Lifecycle Manager reports caller-supplied enabled and active Plugin
status descriptors, including declared dependencies. It is ordered and
read-only.

It never discovers, installs, enables, disables, loads, executes, shuts down,
or removes a plugin. Those operations remain owned by the existing
`PluginManager`.
