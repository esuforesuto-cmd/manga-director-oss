# Backend Selection Example

Run `PYTHONPATH=src python examples/backend_selection/show_selection.py` to
resolve a registered backend preset without generating an image. The example
uses Image Backend Runtime metadata only and does not contact a backend.

See [Backend Selection](../../docs/BACKEND_SELECTION.md) for v2.5 candidate
review criteria. New backends must use the existing ImageGenerator Factory and
preserve the persisted-storyboard and one-page contracts.
