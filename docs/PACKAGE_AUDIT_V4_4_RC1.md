# v4.4 RC1 Package Audit

The RC package audit verifies that the `4.4.0rc1` dynamic version source is
propagated to the wheel and source distribution, package exports remain
available, `py.typed` and `LICENSE` are included, optional extras remain
declared, and generated metadata passes Twine validation.

The RC1 wheel and sdist were built successfully; Twine metadata validation
passed for both. An artifact smoke import from an installed wheel target
confirmed version `4.4.0rc1` and the Enterprise Governance export. The wheel
also contains `py.typed` and the packaged MIT license. Hosted publication,
signing, and registry upload are intentionally outside this local RC review.

See the [release checklist](RELEASE_CHECKLIST_V4_4_RC1.md).
