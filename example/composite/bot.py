"""Сборка всех компонентов приложения — выполняется один раз при старте."""

from uuid import UUID

"""Точка входа Falcon WSGI-приложения."""
import falcon
import urllib3
from classic.signals import Hub
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
from pybotx.auth import BotXAuthVersion
from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.callbacks.callback_manager import CallbackManager
from pybotx.bot.callbacks.callback_memory_repo import CallbackMemoryRepo
from pybotx.client.client import Client
from pybotx.constants import BOTX_DEFAULT_TIMEOUT

hub = Hub()
echo = EchoUseCase()
notify = Notify(hub)
send_mail = SendMail()

# Константы
BOT_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
CTS_URL = "https://cts.example.com"
SECRET_KEY = "secret"

# Создать общие низкоуровневые зависимости ОДИН РАЗ
bot_accounts_storage = BotAccountsStorage(
    [
        BotAccountWithSecret(
            id=BOT_ID,
            cts_url=CTS_URL,
            secret_key=SECRET_KEY,
        )
    ],
    auth_version=BotXAuthVersion.V2,
)

http_client = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=10.0, read=BOTX_DEFAULT_TIMEOUT),
    retries=False,
)

callbacks_manager = CallbackManager(CallbackMemoryRepo())

# Создать НЕЗАВИСИМЫЙ Client
client = Client(
    bot_accounts_storage=bot_accounts_storage,
    http_client=http_client,
    callbacks_manager=callbacks_manager,
    default_callback_timeout=BOTX_DEFAULT_TIMEOUT,
)

# Создать НЕЗАВИСИМЫЙ Bot (БЕЗ client!)
bot = Bot(
    bot_accounts_storage=bot_accounts_storage,
    callbacks_manager=callbacks_manager,
    http_client=http_client,
    handlers={
        "/echo": CommandHandler(echo),
        "/notify": CommandHandler(notify),
        "send_mail": custom_handlers.SendMailHandler(send_mail),
    },
)

# Receivers получает client напрямую
receivers = Receivers(hub=hub, client=client)


def create_app() -> falcon.App:
    app = falcon.App()

    app.add_route("/command", CommandResource(bot, client))
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
