# Metrics

`MetricsRegistry` retains in-process workflow and agent counters plus duration
summaries. Adapter, repository, batch, and project composition roots may use
the same registry without coupling to a monitoring vendor.
