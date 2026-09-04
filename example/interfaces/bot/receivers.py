from uuid import UUID

from classic.signals import Hub

from example.app.usecases.notify import Notification
from pybotx import Client

# Константы для примера (должны быть из конфигурации)
BOT_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
NOTIFY_CHAT_ID = UUID("00000000-0000-0000-0000-000000000001")


class Receivers:

    def __init__(self, hub: Hub, client: Client):
        self._hub=hub
        self._hub.add_reaction(Notification, self.send_notification_to_chat)
        self._client = client

    def send_notification_to_chat(self, notification: Notification) -> None:
        """Обработчик сигнала: отправляет уведомление в BotX-чат."""
        self._client.send_message(
            bot_id=BOT_ID,
            chat_id=NOTIFY_CHAT_ID,
            body=notification.text,
        )
