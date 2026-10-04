# v4.3.0 Package Audit

The final local package validation confirms:

- Dynamic package version resolves to `4.3.0`.
- Wheel and sdist build successfully.
- Twine metadata validation passes.
- The wheel contains `py.typed` and the MIT License.
- An isolated artifact-target install imports the package, exposes v4.3
  production services, and passes CLI, FastAPI, and MCP smoke outside the
  source tree using the validation environment's already-installed dependencies.

A dependency-resolving clean install with FastAPI and MCP smoke remains an
exact-tag publication gate because the local dependency-resolution window did
not complete. This does not alter the validated package metadata or artifact
contents.
