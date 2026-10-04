"""Inspect declared image-backend health without generating an image."""

from manga_director.adapters import ImageBackendRuntime

runtime = ImageBackendRuntime()
for snapshot in runtime.health_snapshot():
    print(snapshot.name, snapshot.state)
