"""Resolve an image-backend preset without generating an image."""

from manga_director.adapters import ImageBackendRuntime

if __name__ == "__main__":
    runtime = ImageBackendRuntime()
    print(runtime.resolve("test"))
