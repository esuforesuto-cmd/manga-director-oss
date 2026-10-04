from collections.abc import Callable

from manga_director.notifications.providers import (
    ConsoleNotificationProvider,
    MockNotificationProvider,
    NotificationProvider,
)


class NotificationFactory:
    _builders: dict[str, Callable[[], NotificationProvider]] = {
        "console": ConsoleNotificationProvider,
        "mock": MockNotificationProvider,
    }

    @classmethod
    def register(cls, name: str, builder: Callable[[], NotificationProvider]) -> None:
        cls._builders[name] = builder

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._builders.pop(name, None)

    @classmethod
    def create(cls, name: str) -> NotificationProvider:
        return cls._builders[name]()

    @classmethod
    def available(cls) -> list[str]:
        return sorted(cls._builders)
