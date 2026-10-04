# Database

`SQLiteRepository` and `PostgreSQLRepository` implement the existing
`ProjectRepository` port through SQLAlchemy 2.x. Configure one at the
composition root; workflow, agents, CLI, MCP, and UI continue to receive only
the repository interface.

```yaml
database_provider: sqlite
database_url: sqlite:///./manga-director.db
```

Use `postgresql+psycopg://user:password@host/database` for PostgreSQL.
