"""Сборка всех компонентов приложения — выполняется один раз при старте."""

from uuid import UUID

import urllib3
from classic.signals import Hub
from waitress import serve

from example.app.usecases.echo import EchoUseCase
from example.app.usecases.handle_callback import HandleCallback
from example.app.usecases.notify import Notify
from example.app.usecases.send_mail import SendMail
from example.interfaces.bot import custom_handlers
from example.interfaces.bot.receivers import Receivers
from pybotx import BotAccountWithSecret, Client, Command, create_botx_app
from pybotx.auth import BotXAuthVersion
from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.constants import BOTX_DEFAULT_TIMEOUT

# Инициализация
hub = Hub()
echo = EchoUseCase()
notify = Notify(hub)
send_mail = SendMail()
handle_callback = HandleCallback()

# Константы
BOT_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
CTS_URL = "https://cts.example.com"
SECRET_KEY = "secret"

# Создать bot_accounts_storage
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

# Создать HTTP client
http_client = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=10.0, read=BOTX_DEFAULT_TIMEOUT),
    retries=False,
)

# Создать Client
client = Client(
    bot_accounts_storage=bot_accounts_storage,
    http_client=http_client,
)

# Command handlers
command_handlers = {
    "/echo": Command(echo),
    "/notify": Command(notify),
    "send_mail": custom_handlers.SendMailHandler(send_mail),
}

# Receivers получает client напрямую
receivers = Receivers(hub=hub, client=client)

# Создать app через фабрику
application = create_botx_app(
    credentials=bot_accounts_storage,
    client=client,
    command_handlers=command_handlers,
    callback_handler=handle_callback.execute,  # Обработчик для callback
)


if __name__ == "__main__":
    try:
        serve(application, host="0.0.0.0", port=8000)  # type: ignore[arg-type]
    finally:
        http_client.clear()
