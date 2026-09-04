"""Базовый класс для обработчиков команд бота."""

from typing import TYPE_CHECKING, Any

from pybotx.models.message.incoming_message import IncomingMessage

if TYPE_CHECKING:
    from pybotx.client.client import Client


class CommandHandler:
    """Базовый обработчик команд."""

    def __init__(self, usecase: Any) -> None:
        """Initialize handler with UseCase.

        :param usecase: UseCase instance to execute.
        """
        self._usecase = usecase

    def handle(self, message: IncomingMessage, client: "Client") -> None:
        """Handle incoming message by executing UseCase.

        :param message: Incoming message from BotX.
        :param client: Client instance for sending responses.
        """
        # Извлечь аргументы из message.body
        args = self._parse_args(message.body)

        # Выполнить usecase
        result = self._usecase.execute(*args)

        # Отправить ответ если результат не None
        if result is not None:
            client.send_message(
                bot_id=message.bot.id,
                chat_id=message.chat.id,
                body=str(result),
            )

    def _parse_args(self, body: str) -> tuple:
        """Parse arguments from message body.

        :param body: Message body (e.g., "/echo Hello world").
        :return: Tuple of arguments.
        """
        # Разделить body на команду и аргументы
        parts = body.split(maxsplit=1)
        # Вернуть аргументы (все после команды) или пустой tuple
        return (parts[1],) if len(parts) > 1 else ()
