"""Сборка всех компонентов приложения — выполняется один раз при старте."""

from uuid import UUID

"""Точка входа Falcon WSGI-приложения."""
import falcon
from classic.signals import Hub
from example.infrastructure.database.mock_db import MockDatabase
from waitress import serve

from example.app.usecases.echo import EchoUseCase
from example.app.usecases.notify import Notify
from example.app.usecases.send_mail import SendMail
from example.interfaces.bot import custom_handlers
from example.interfaces.bot.receivers import Receivers
from example.interfaces.bot.resources import (
    CallbackResource,
    CommandResource,
    StatusResource,
)
from pybotx import Bot, BotAccountWithSecret, BotMenu, CommandHandler

hub = Hub()
echo = EchoUseCase()
notify = Notify(hub)
send_mail = SendMail()
# -- бот -- Callback - добавить в либу
#
BOT_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
CTS_URL = "https://cts.example.com"
SECRET_KEY = "secret"

bot = Bot(
    bot_accounts=[
        BotAccountWithSecret(
            id=BOT_ID,
            cts_url=CTS_URL,
            secret_key=SECRET_KEY,
        )
    ],
    handlers={
        "/echo": CommandHandler(echo),
        "/notify": CommandHandler(notify),
        "send_mail": custom_handlers.SendMailHandler(send_mail),
    },
)

receivers = Receivers(hub=hub, client=bot.client)


def create_app() -> falcon.App:
    app = falcon.App()

    app.add_route("/command", CommandResource(bot))
    app.add_route("/status", StatusResource(bot))
    app.add_route("/notification/callback", CallbackResource(bot))

    return app


application = create_app()


if __name__ == "__main__":
    bot.startup()
    try:
        serve(application, host="0.0.0.0", port=8000)  # type: ignore[arg-type]
    finally:
        bot.shutdown()
