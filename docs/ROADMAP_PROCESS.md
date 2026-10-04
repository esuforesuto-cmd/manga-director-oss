# Roadmap and Issue Process

1. Propose work in a GitHub Issue using the v2.3 taxonomy and milestone.
2. State affected public contracts, architectural boundary, risk, rollback,
   test plan, documentation plan, and out-of-scope items.
3. Attach a design record for Provider, Image Backend, Enterprise, security,
   persistence, or performance work before code is approved.
4. Use mock fixtures for CI; network credentials and live integrations are not
   required or accepted in the default test suite.
5. Require the v2.3 quality gates and update benchmarks when a measured path
   changes.
6. Close the Issue only with compatibility, security, documentation, and
   release-note evidence.

Maintainers may defer a proposal to v3 when it requires a Core redesign,
distributed execution, a marketplace, or a cloud control plane.
