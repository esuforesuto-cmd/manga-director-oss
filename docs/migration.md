# Migrations

Alembic assets are in `migrations/`. Set `sqlalchemy.url` in `alembic.ini` or
pass `-x` configuration through deployment tooling, then run `alembic upgrade
head`. Revision `0001_initial` creates Project, Chapter, and Page tables.
