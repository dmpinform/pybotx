# pybotx

Синхронная Python-библиотека для работы с BotX API.

Библиотека отвечает за три вещи: разбор входящих команд, формирование исходящих запросов к BotX и верификацию подписей. Маршрутизация, обработка ошибок и управление конкурентностью остаются на стороне приложения.

## Установка

```
pip install pybotx
```

## Концепция

BotX общается с ботом через три HTTP-эндпоинта:

| Метод | Путь | Назначение |
|-------|------|------------|
| `POST` | `/command` | Входящие сообщения и системные события |
| `GET` | `/status` | Меню бота (список команд) |
| `POST` | `/notification/callback` | Async-результаты от BotX |

Приложение регистрирует эти эндпоинты в любом WSGI/ASGI-фреймворке и делегирует обработку объекту `Bot`.

## Быстрый старт

### 1. Создание бота

```python
from uuid import UUID
from pybotx import Bot, BotAccountWithSecret, BotMenu

bot = Bot(
    bot_accounts=[
        BotAccountWithSecret(
            id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            cts_url="https://cts.example.com",
            secret_key="your-secret-key",
        )
    ],
    bot_menu=BotMenu({
        "/echo": "Вернуть сообщение обратно",
        "/help": "Список команд",
    }),
)
```

### 2. Жизненный цикл

```python
bot.startup()   # получить токены при BotXAuthVersion.V1
# ... сервер обрабатывает запросы ...
bot.shutdown()  # закрыть HTTP-клиент, отменить ожидание колбэков
```

### 3. Разбор входящей команды

`parse_bot_command` принимает тело POST-запроса и заголовки, проверяет подпись и возвращает типизированный объект.

```python
from pybotx import Bot, IncomingMessage, UnverifiedRequestError

bot_command = bot.parse_bot_command(
    request.json,
    request_headers=dict(request.headers),
)

if isinstance(bot_command, IncomingMessage):
    print(bot_command.body)      # "/echo hello"
    print(bot_command.argument)  # "hello"
    print(bot_command.bot.id)    # UUID бота
    print(bot_command.chat.id)   # UUID чата
    print(bot_command.sender.huid)
```

При невалидной подписи поднимается `UnverifiedRequestError`.

### 4. Статус-эндпоинт

```python
status = bot.get_raw_status(
    dict(request.query_params),
    request_headers=dict(request.headers),
)
# status — готовый dict, сериализуется в JSON
```

### 5. Колбэк-эндпоинт

BotX присылает результат async-метода (например, `send_message`) отдельным POST-запросом. `parse_callback` регистрирует его в менеджере колбэков — поток, вызвавший `send_message`, разблокируется.

```python
bot.parse_callback(
    request.json,
    request_headers=dict(request.headers),
)
```

### 6. Отправка сообщения

```python
from uuid import UUID

bot.send_message(
    bot_id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
    chat_id=UUID("30dc1980-643a-00ad-37fc-7cc10d74e935"),
    body="Привет!",
)
```

По умолчанию вызов блокируется до получения колбэка от BotX (`wait_callback=True`). Для серверов BotX ≥ 3.58 можно использовать `send_message_sync` — прямой ответ без колбэка.

## Паттерны интеграции

### Паттерн 1 — Контроллер

Подходит, когда бот — основной пользовательский интерфейс приложения. Контроллер владеет ботом и юзкейсами, маршрутизирует команды вручную.

```python
# bot_controller.py
from pybotx import Bot, IncomingMessage
from myapp.usecases import EchoUseCase

class BotController:
    def __init__(self, bot: Bot, echo_uc: EchoUseCase) -> None:
        self._bot = bot
        self._echo_uc = echo_uc

    def dispatch(self, message: IncomingMessage) -> None:
        command = message.body.split()[0]
        if command == "/echo":
            text = self._echo_uc.execute(message.argument)
            self._bot.send_message(
                bot_id=message.bot.id,
                chat_id=message.chat.id,
                body=text,
            )

# deps.py
bot = Bot(bot_accounts=[...])
controller = BotController(bot=bot, echo_uc=EchoUseCase())
```

### Паттерн 2 — Наблюдатель

Подходит, когда бот — канал доставки уведомлений от фоновых процессов. Юзкейс не знает о боте; бот подписывается на события через колбэк.

```python
# usecases/notify.py
from collections.abc import Callable

class NotifyUseCase:
    def __init__(self) -> None:
        self._handlers: list[Callable[[str], None]] = []

    def subscribe(self, handler: Callable[[str], None]) -> None:
        self._handlers.append(handler)

    def execute(self, text: str) -> None:
        for handler in self._handlers:
            handler(text)

# deps.py
from uuid import UUID
from pybotx import Bot, BotAccountWithSecret

BOT_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
NOTIFY_CHAT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

bot = Bot(bot_accounts=[...])
notify_uc = NotifyUseCase()

notify_uc.subscribe(
    lambda text: bot.send_message(bot_id=BOT_ID, chat_id=NOTIFY_CHAT_ID, body=text)
)
```

Теперь любой сервис вызывает `notify_uc.execute("текст")` — сообщение уходит в BotX-чат.

## Полный пример (Falcon + Waitress)

Минимальное рабочее приложение находится в `example/app/`. Запуск:

```
python -m example.app.main
```

### `example/app/resources.py`

```python
import falcon
from pybotx import IncomingMessage, UnverifiedRequestError
from pybotx.bot.api.responses.command_accepted import build_command_accepted_response
from pybotx.bot.api.responses.unverified_request import build_unverified_request_response
from example.app.deps import bot, controller

class CommandResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        try:
            bot_command = bot.parse_bot_command(
                req.media,
                request_headers=dict(req.headers),
            )
        except UnverifiedRequestError:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response()
            return

        if isinstance(bot_command, IncomingMessage):
            controller.dispatch(bot_command)

        resp.media = build_command_accepted_response()

class StatusResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        try:
            resp.media = bot.get_raw_status(
                dict(req.params),
                request_headers=dict(req.headers),
            )
        except UnverifiedRequestError:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response()

class CallbackResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        try:
            bot.parse_callback(req.media, request_headers=dict(req.headers))
        except UnverifiedRequestError:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response()
            return
        resp.media = {"status": "ok"}
```

## Системные события

Помимо `IncomingMessage` `parse_bot_command` может вернуть системное событие. Обработка через `isinstance`:

```python
from pybotx import (
    AddedToChatEvent,
    ChatCreatedEvent,
    DeletedFromChatEvent,
    IncomingMessage,
)

bot_command = bot.parse_bot_command(raw, request_headers=headers)

if isinstance(bot_command, IncomingMessage):
    controller.dispatch(bot_command)
elif isinstance(bot_command, AddedToChatEvent):
    on_added_to_chat(bot_command)
elif isinstance(bot_command, ChatCreatedEvent):
    on_chat_created(bot_command)
```

## Конфигурация `Bot`

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|-------------|----------|
| `bot_accounts` | `Sequence[BotAccountWithSecret]` | — | Список аккаунтов бота |
| `bot_menu` | `BotMenu \| None` | `BotMenu({})` | Меню команд для `/status` |
| `httpx_client` | `httpx.Client \| None` | новый клиент | Кастомный HTTP-клиент |
| `default_callback_timeout` | `float` | 60 с | Таймаут ожидания колбэка |
| `callback_repo` | `CallbackRepoProto \| None` | in-memory | Хранилище колбэков |
| `auth_version` | `BotXAuthVersion` | `V2` | Версия аутентификации |

## Аутентификация

| Версия | Описание |
|--------|----------|
| `BotXAuthVersion.V2` | JWT подписывается секретом бота, `iss` = UUID бота. Токен не нужен. |
| `BotXAuthVersion.V1` | Токен получается от BotX-сервера при `startup()`. |

## Основные методы отправки

```python
# Сообщение в чат (async, ждёт колбэк)
bot.send_message(bot_id=..., chat_id=..., body="текст")

# Сообщение без колбэка (BotX >= 3.58)
bot.send_message_sync(bot_id=..., chat_id=..., body="текст")

# Редактирование сообщения
bot.edit_message(bot_id=..., sync_id=..., body="новый текст")

# Ответ на сообщение
bot.reply(bot_id=..., sync_id=..., body="ответ")
```

Полный список методов API: `send_message`, `send_message_sync`, `edit_message`, `reply`, `create_chat`, `add_user`, `remove_user`, `chat_info`, `upload_file`, `download_file`, `get_user_by_huid` и другие — см. `pybotx/bot/bot.py`.
