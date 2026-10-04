# Knowledge Platform Planning

Knowledge Platform candidates organize existing Repository-derived knowledge
into catalog, relationship, search-strategy, quality-metric, governance, and
insight DTOs. Each proposal must document source provenance, redaction,
retention, ownership, deterministic fixtures, and an explicit no-write proof.

Catalog and relationships are projections, not a replacement Knowledge store.
Search strategy is local and supplied-input only. Quality and governance are
diagnostic and cannot correct, merge, retain, archive, or delete knowledge.

See [v3.4 roadmap](ROADMAP_v3_4.md) and
[Architecture Planning](ARCHITECTURE_V3_4.md).

## v6.0 Creative Production Platform extension

v6.0 retains these constraints and extends the design to a provenance-bearing
Creative Knowledge Graph. Story, character, world, asset, production, review,
and publication references remain source-owned records connected through
stable identifiers. The graph is a query and explanation layer, not a new
repository or automatic correction engine.

Planned contracts include bounded node/edge traversal, source provenance,
confidence, retention classification, redaction labels, and human review
references. Search and recommendation are opt-in and advisory; they cannot
merge, delete, archive, publish, or alter any source record.

## v6.1 metadata descriptor contract

The v6.1 node metadata descriptor is an opt-in, read-only completeness report
over caller-supplied v6.0 Knowledge Graph nodes. Confidence, retention
classification, and redaction are opaque caller labels; they are neither
ranked nor enforced. `human_retention_decision` and `review_required=True`
preserve existing human-owned policy and review boundaries without retention,
redaction, review, or approval execution.

## v6.1 bounded traversal read model

The v6.1 traversal service is an opt-in, local read model over a supplied
Knowledge Graph report. It provides bounded outgoing breadth-first traversal
and immutable node/edge snapshots only. It neither depends on metadata
descriptors nor introduces repository, graph-store, indexing, remote retrieval,
or automated policy behavior.
