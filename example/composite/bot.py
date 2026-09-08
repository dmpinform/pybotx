"""Сборка всех компонентов приложения — выполняется один раз при старте."""

from uuid import UUID

import urllib3
from classic.signals import Hub
from waitress import serve

from example.app.usecases.echo import EchoUseCase
from example.app.usecases.handle_callback import HandleCallback
from example.app.usecases.notify import Notify
from example.app.usecases.send_mail import SendMail
from example.interfaces.bot import custom_command
from example.interfaces.bot.receivers import Receivers
from pybotx import Callback, Client, Command, create_botx_app
from pybotx.constants import BOTX_DEFAULT_TIMEOUT

# Константы
BOT_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
CTS_URL = "https://cts.example.com"
SECRET_KEY = "secret"

# Создать HTTP client
http_client = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=10.0, read=BOTX_DEFAULT_TIMEOUT),
    retries=False,
)

# Создать Client
client = Client(
    bot_id=BOT_ID,
    cts_url=CTS_URL,
    secret_key=SECRET_KEY,
    http_client=http_client,
)

# Usecases
hub = Hub()
echo = EchoUseCase(client)
notify = Notify(hub)
send_mail = SendMail()
handle_callback = HandleCallback()
# Signals
receivers = Receivers(hub=hub, client=client)
# Command handlers
commands = {
    "/echo": Command(echo),
    "/send_mail": custom_command.SendMailCommand(send_mail, client),
}
# Callback handlers
callback = Callback(handle_callback)

# Создать app через фабрику
application = create_botx_app(
    client=client,
    commands=commands,
    callback=callback,
)


if __name__ == "__main__":
    try:
        serve(application, host="0.0.0.0", port=8000)  # type: ignore[arg-type]
    finally:
        http_client.clear()
