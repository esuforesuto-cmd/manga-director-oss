from collections.abc import Callable

from manga_director.repositories.database import (
    DatabaseRepository,
    PostgreSQLRepository,
    SQLiteRepository,
)

DatabaseBuilder = Callable[[str], DatabaseRepository]


class DatabaseFactory:
    _builders: dict[str, DatabaseBuilder] = {
        "sqlite": SQLiteRepository,
        "postgresql": PostgreSQLRepository,
    }

    @classmethod
    def register(cls, provider: str, builder: DatabaseBuilder) -> None:
        cls._builders[provider] = builder

    @classmethod
    def create(cls, provider: str, url: str) -> DatabaseRepository:
        try:
            return cls._builders[provider](url)
        except KeyError as exc:
            raise ValueError(f"Unsupported database provider: {provider}") from exc

    @classmethod
    def available(cls) -> list[str]:
        return sorted(cls._builders)
