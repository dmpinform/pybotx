from uuid import UUID

from classic.signals import Hub
from pydantic.dataclasses import dataclass

from pybotx import IncomingMessage


@dataclass
class Notification:
    bot_id: UUID
    chat_id: UUID
    text: str


class Notify:
    """Паттерн наблюдатель: подписчики получают уведомление при вызове execute."""

    def __init__(self, hub: Hub) -> None:
        self._hub = hub

    def execute(self, message: IncomingMessage) -> None:
        """Выполнить уведомление — отправить сигнал всем подписчикам."""
        self._hub.notify(
            Notification(
                bot_id=message.bot.id,
                chat_id=message.chat.id,
                text=message.argument,
            ),
        )
