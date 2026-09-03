from classic.signals import Hub
from pydantic.dataclasses import dataclass

@dataclass
class Notification:
    text: str

class Notify:
    """Паттерн наблюдатель: подписчики получают уведомление при вызове execute."""
    def __init__(self, hub: Hub) -> None:
        self._hub=hub

    def execute(self, text: str) -> None:
        """Выполнить уведомление - отправить сигнал всем подписчикам."""
        self._hub.notify(Notification(text=text))
