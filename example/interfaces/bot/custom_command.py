"""Кастомные обработчики команд."""

from typing import Any

from pybotx import Client, IncomingMessage
from pybotx.bot.command import Command


class SendMailCommand(Command):
    """Кастомный обработчик для отправки email."""

    def __init__(self, usecase: Any, client: Client):
        super().__init__(usecase)
        self._client = client

    def execute(self, message: IncomingMessage) -> None:
        """Execute send_mail command.

        :param message: Incoming message from BotX.
        :param client: Client instance for sending responses.
        """

        # Выполнить usecase
        result = self._usecase.run(message)

        # Отправить подтверждение в чат
        self._client.send_message(
            bot_id=message.bot.id,
            chat_id=message.chat.id,
            body=f"Email sent: {result}",
        )
