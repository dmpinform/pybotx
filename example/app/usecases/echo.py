from pybotx import Client, IncomingMessage


class EchoUseCase:
    def __init__(self, client: Client) -> None:
        self._client = client

    def execute(self, message: IncomingMessage) -> None:
        self._client.send_message(
            bot_id=message.bot.id,
            chat_id=message.chat.id,
            body=message.argument or "echo: (empty)",
        )
