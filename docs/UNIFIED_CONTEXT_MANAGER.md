# Unified Context Manager

## v6.0 Iteration 3

The Unified Context Manager reuses the existing Unified Platform context
factory together with the v6 Context Engine. It correlates caller-supplied
workspace, knowledge, agent, and production references for exactly one Page.

The manager neither loads nor persists source contexts, and it never generates
a prompt or changes workflow state.
