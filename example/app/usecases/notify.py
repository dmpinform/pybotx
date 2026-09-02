from collections.abc import Callable


class NotifyUseCase:
    """Паттерн наблюдатель: подписчики получают уведомление при вызове execute."""

    def __init__(self) -> None:
        self._handlers: list[Callable[[str], None]] = []

    def subscribe(self, handler: Callable[[str], None]) -> None:
        self._handlers.append(handler)

    def execute(self, text: str) -> None:
        for handler in self._handlers:
            handler(text)
