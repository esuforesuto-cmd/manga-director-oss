# Webhook security

Webhook delivery requires HTTPS, validates hosts, blocks private/loopback DNS
results by default, rejects redirects, signs payloads with HMAC SHA-256, adds a
timestamp and event ID, limits response reads, and applies a timeout.
