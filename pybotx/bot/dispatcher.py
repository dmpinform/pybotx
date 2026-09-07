"""Command dispatcher for routing incoming messages to handlers."""

from typing import TYPE_CHECKING, Any

from pybotx.models.message.incoming_message import IncomingMessage

if TYPE_CHECKING:
    from pybotx.bot.command import Command
    from pybotx.client.client import Client


class CommandDispatcher:
    """Dispatcher for routing commands to handlers."""

    def __init__(self, handlers: dict[str, "Command"]) -> None:
        """Initialize dispatcher with handlers.

        :param handlers: Dict mapping command strings to Command instances.
                        Example: {"/echo": Command(EchoUseCase()), "/help": Command(HelpUseCase())}
        """
        self._handlers = handlers

    def dispatch(self, message: IncomingMessage, client: "Client") -> None:
        """Dispatch message to appropriate handler.

        :param message: IncomingMessage from BotX.
        :param client: Client instance for API calls.
        """
        # Извлечь команду из тела сообщения (например, "/echo")
        command = message.body.split()[0] if message.body else ""

        # Найти handler для команды
        handler = self._handlers.get(command)

        # Вызвать handler если он существует
        if handler:
            handler.execute(message, client)
