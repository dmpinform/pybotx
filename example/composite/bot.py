"""Сборка всех компонентов приложения — выполняется один раз при старте."""

from uuid import UUID

"""Точка входа Falcon WSGI-приложения."""
import falcon
from classic.signals import Hub
from example.app.bot_controller import BotController
from example.app.deps import bot
from example.app.resources import CallbackResource, CommandResource, StatusResource
from waitress import serve

from example.app.usecases.echo import EchoUseCase
from example.app.usecases.notify import Notify
from example.app.usecases.send_mail import SendMail
from example.interfaces.bot import callbacks
from example.interfaces.bot.receivers import Receivers
from pybotx import Bot, BotAccountWithSecret, BotMenu, Callback

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
    bot_menu=BotMenu(
        {
            "/echo": "Вернуть сообщение обратно",
            "/notify": "Отправить уведомление подписчикам",
        }
    ),
    callbacks={
        "notify": Callback(echo),
        "echo": Callback(notify),
        "send_mail": callbacks.SendMail(send_mail),
    },
)

receivers = Receivers(hub=hub, client=bot.client)


def create_app() -> falcon.App:
    app = falcon.App()

    app.add_route("/command", CommandResource())
    app.add_route("/status", StatusResource())
    app.add_route("/notification/callback", CallbackResource())

    return app


application = create_app()


if __name__ == "__main__":
    bot.startup()
    try:
        serve(application, host="0.0.0.0", port=8000)  # type: ignore[arg-type]
    finally:
        bot.shutdown()
