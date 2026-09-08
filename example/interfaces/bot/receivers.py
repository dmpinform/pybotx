from classic.signals import Hub

from example.app.usecases.notify import Notification
from pybotx import Client


class Receivers:
    def __init__(self, hub: Hub, client: Client):
        self._client = client
        self._hub = hub
        self._hub.add_reaction(Notification, self.send_notification_to_chat)

    def send_notification_to_chat(self, notification: Notification) -> None:
        """Обработчик сигнала: отправляет уведомление в BotX-чат."""
        self._client.send_message(
            bot_id=notification.bot_id,
            chat_id=notification.chat_id,
            body=notification.text,
        )
