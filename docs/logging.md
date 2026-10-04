# Logging

Library modules use `logging.getLogger(__name__)`; they never use `print` for
operational output. Applications may select plain-text or JSON handlers without
changing Core behavior.

| Level | Use |
| --- | --- |
| `DEBUG` | Diagnostic context that is safe to retain locally. |
| `INFO` | Workflow lifecycle and successful high-level operations. |
| `WARNING` | Recoverable adapter, validation, or delivery anomalies. |
| `ERROR` | Failed operations requiring intervention. |

Never log API keys, access tokens, passwords, cookies, webhook secrets,
authorization headers, raw signatures, or unredacted request bodies. Prefer
project ID, page number, trace ID, event type, provider-neutral status, and a
safe error code.
