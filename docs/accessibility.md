# Accessibility

The minimal UI applies the following baseline practices:

- semantic headings and landmark structure
- labels for all form inputs
- keyboard-visible focus styles
- accessible button labels and table headings
- `role="alert"` for action failures
- `aria-live="polite"` for pending action outcomes
- responsive layouts that preserve content hierarchy at narrow widths

Before a production release, validate all primary views with keyboard-only
navigation, a screen reader, automated accessibility checks, and real content
with long project names and error messages.
