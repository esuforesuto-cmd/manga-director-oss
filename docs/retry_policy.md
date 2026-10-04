# Retry policy

Retries use bounded exponential backoff and only configured retryable HTTP
statuses. Invalid URLs and client errors are not retried.
