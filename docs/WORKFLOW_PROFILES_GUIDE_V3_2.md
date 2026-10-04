# v3.2.0 Workflow Profiles Guide

Workflow Profiles describe the current Page StateMachine and pipeline without
changing it. A profile includes every known stage, highlights the current stage,
and uses `StateMachine.next_command()` solely to display the legal next command.

Profiles never execute a workflow, transition a context, create another Page,
generate an image, or enable automatic approval. Use them for inspection,
diagnostics, and human planning only.
