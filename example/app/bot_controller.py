from collections.abc import Callable

from pybotx import Bot, IncomingMessage

from example.app.usecases.echo import EchoUseCase
from example.app.usecases.notify import NotifyUseCase


class BotController:
    """Контроллер: принимает IncomingMessage, вызывает нужный юзкейс."""

    def __init__(
        self,
        bot: Bot,
        echo_uc: EchoUseCase,
        notify_uc: NotifyUseCase,
    ) -> None:
        self._bot = bot
        self._echo_uc = echo_uc
        self._notify_uc = notify_uc

        self._commands: dict[str, Callable[[IncomingMessage], None]] = {
            "/echo": self.echo,
            "/notify": self.notify,
        }

    def dispatch(self, message: IncomingMessage) -> None:
        command = message.body.split()[0]
        handler = self._commands.get(command)
        if handler:
            handler(message)

    def echo(self, message: IncomingMessage) -> None:
        text = self._echo_uc.execute(message.argument)
        self._bot.send_message(
            bot_id=message.bot.id,
            chat_id=message.chat.id,
            body=text,
        )

    def notify(self, message: IncomingMessage) -> None:
        self._notify_uc.execute(message.argument)
