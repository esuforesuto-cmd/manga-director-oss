# Webhook example

This example deliberately uses `MockNotificationProvider`; it makes no network
call and is safe for local development and CI. `WebhookNotificationProvider`
requires an allowed HTTPS host and a secret obtained outside `config.yaml`.
See [Notification](../../docs/notification.md) and
[Webhook security](../../docs/webhook_security.md).
