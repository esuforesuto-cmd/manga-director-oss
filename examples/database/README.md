# Database example

Run `PYTHONPATH=src python examples/database/sqlite.py` to use the synchronous
SQLite adapter through the Repository boundary. Production database selection
remains configuration/factory driven; workflow code must never select a concrete
database implementation. See [Database](../../docs/database.md).
