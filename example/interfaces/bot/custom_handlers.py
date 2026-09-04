"""Кастомные обработчики команд."""

from pybotx import Client, CommandHandler, IncomingMessage


class SendMailHandler(CommandHandler):
    """Кастомный обработчик для отправки email."""

    def handle(self, message: IncomingMessage, client: Client) -> None:
        """Handle send_mail command.

        :param message: Incoming message from BotX.
        :param client: Client instance for sending responses.
        """
        # Извлечь аргументы
        args = self._parse_args(message.body)
        email_text = args[0] if args else "Empty message"

        # Выполнить usecase
        result = self._usecase.run(email_text)

        # Отправить подтверждение в чат
        client.send_message(
            bot_id=message.bot.id,
            chat_id=message.chat.id,
            body=f"Email sent: {result}",
        )
