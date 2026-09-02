"""Сборка всех компонентов приложения — выполняется один раз при старте."""
from uuid import UUID

from pybotx import Bot, BotAccountWithSecret, BotMenu

from example.app.bot_controller import BotController
from example.app.usecases.echo import EchoUseCase
from example.app.usecases.notify import NotifyUseCase

BOT_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
CTS_URL = "https://cts.example.com"
SECRET_KEY = "secret"

# -- Инстанцирование --

bot = Bot(
    bot_accounts=[
        BotAccountWithSecret(
            id=BOT_ID,
            cts_url=CTS_URL,
            secret_key=SECRET_KEY,
        )
    ],
    bot_menu=BotMenu({
        "/echo": "Вернуть сообщение обратно",
        "/notify": "Отправить уведомление подписчикам",
    }),
)

echo_uc = EchoUseCase()
notify_uc = NotifyUseCase()

controller = BotController(bot=bot, echo_uc=echo_uc, notify_uc=notify_uc)

# -- Паттерн наблюдатель --
# Бот-команда подписывается на юзкейс уведомлений.
# Когда notify_uc.execute() вызывается из любого места приложения,
# сообщение автоматически уходит в BotX-чат.
NOTIFY_CHAT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

notify_uc.subscribe(
    lambda text: bot.send_message(
        bot_id=BOT_ID,
        chat_id=NOTIFY_CHAT_ID,
        body=text,
    )
)
