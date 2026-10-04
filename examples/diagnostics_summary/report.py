"""Export a transport-neutral enterprise diagnostics report."""

from manga_director.cli.config import AppConfig
from manga_director.observability import EnterpriseDiagnostics

print(EnterpriseDiagnostics(config=AppConfig()).report().to_markdown())
