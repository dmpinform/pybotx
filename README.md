# pybotx

Синхронная Python-библиотека для работы с BotX API.

Библиотека отвечает за три вещи: разбор входящих команд, формирование исходящих запросов к BotX и верификацию подписей. Маршрутизация, обработка ошибок и управление конкурентностью остаются на стороне приложения.

## Установка

```bash
pip install pybotx
```

## Архитектура

Библиотека разделена на три основных компонента:

- **`Bot`** — диспетчеризация входящих запросов, верификация JWT, жизненный цикл
- **`Client`** — отправка API запросов к BotX (messages, chats, files, users и т.д.)
- **`CommandHandler`** — базовый класс для обработчиков команд

```
┌─────────────┐
│   BotX API  │
└──────┬──────┘
       │
       │ HTTP
       ▼
┌─────────────┐         ┌──────────────┐
│     Bot     │◄────────┤ BotAccounts  │
│             │         │   Storage    │
│ - parse     │         └──────┬───────┘
│ - verify    │                │ shared
│ - dispatch  │                │
└──────┬──────┘                │
       │ owns                  │
       ▼                       │
┌─────────────┐                │
│   Client    │◄───────────────┘
│             │
│ - send_msg  │
│ - create    │
│ - search    │
└─────────────┘
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
from pybotx import Bot, BotAccountWithSecret, BotMenu, CommandHandler

# UseCase
class EchoUseCase:
    def execute(self, text: str) -> str:
        return text

echo = EchoUseCase()

# Bot с handlers
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
    handlers={
        "/echo": CommandHandler(echo),
    },
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
    
    # Автоматическая диспетчеризация
    bot.dispatch_command(bot_command)
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

### 6. Отправка сообщения через Client

```python
from uuid import UUID

# Client доступен через bot.client
bot.client.send_message(
    bot_id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
    chat_id=UUID("30dc1980-643a-00ad-37fc-7cc10d74e935"),
    body="Привет!",
)
```

По умолчанию вызов блокируется до получения колбэка от BotX (`wait_callback=True`). Для серверов BotX ≥ 3.58 можно использовать `send_message_sync` — прямой ответ без колбэка.

## CommandHandler

`CommandHandler` — базовый класс для обработчиков команд. Автоматически:
- Извлекает аргументы из `message.body`
- Вызывает `usecase.execute(*args)`
- Отправляет результат через `client.send_message()`

### Базовое использование

```python
from pybotx import CommandHandler

class EchoUseCase:
    def execute(self, text: str) -> str:
        return text

bot = Bot(
    bot_accounts=[...],
    handlers={
        "/echo": CommandHandler(EchoUseCase()),
    },
)
```

### Кастомный handler

Наследуйте `CommandHandler` для сложной логики:

```python
from pybotx import CommandHandler, Client, IncomingMessage

class NotifyHandler(CommandHandler):
    def __init__(self, notify_usecase):
        super().__init__(notify_usecase)
    
    def handle(self, message: IncomingMessage, client: Client) -> None:
        # Кастомная обработка
        args = self._parse_args(message.body)
        
        # Выполнить usecase
        self._usecase.execute(args[0])
        
        # Кастомный ответ
        client.send_message(
            bot_id=message.bot.id,
            chat_id=message.chat.id,
            body="✅ Уведомление отправлено",
        )

bot = Bot(
    handlers={
        "/notify": NotifyHandler(notify_usecase),
    },
)
```

## Паттерны интеграции

### Паттерн 1 — CommandHandler (Рекомендуется)

Подходит для простых команд с минимальной логикой.

```python
from pybotx import Bot, BotAccountWithSecret, CommandHandler

# UseCases
class EchoUseCase:
    def execute(self, text: str) -> str:
        return text

class HelpUseCase:
    def execute(self) -> str:
        return "Доступные команды: /echo, /help"

# Сборка
bot = Bot(
    bot_accounts=[...],
    handlers={
        "/echo": CommandHandler(EchoUseCase()),
        "/help": CommandHandler(HelpUseCase()),
    },
)
```

### Паттерн 2 — Наблюдатель (Observer)

Подходит, когда бот — канал доставки уведомлений от фоновых процессов. UseCase не знает о боте; внешний receiver подписывается на события.

```python
# usecases/notify.py
from classic.signals import Hub
from pydantic.dataclasses import dataclass

@dataclass
class Notification:
    text: str

class NotifyUseCase:
    def __init__(self, hub: Hub) -> None:
        self._hub = hub
    
    def execute(self, text: str) -> None:
        # Отправить событие всем подписчикам
        self._hub.notify(Notification(text=text))

# receivers.py
from uuid import UUID
from classic.signals import Hub
from pybotx import Client

class Receivers:
    def __init__(self, hub: Hub, client: Client):
        self._client = client
        # Подписаться на события
        hub.add_reaction(Notification, self.send_to_botx)
    
    def send_to_botx(self, notification: Notification) -> None:
        self._client.send_message(
            bot_id=UUID("..."),
            chat_id=UUID("..."),
            body=notification.text,
        )

# composite.py
hub = Hub()
bot = Bot(bot_accounts=[...])
notify_uc = NotifyUseCase(hub)
receivers = Receivers(hub, bot.client)

# Теперь любой вызов notify_uc.execute("текст") отправит сообщение в BotX
```

**Преимущества:**
- UseCase не зависит от BotX (можно добавить другие каналы: email, SMS)
- Множественные подписчики на одно событие
- Слабая связанность компонентов

## Полный пример (Falcon + Waitress)

Минимальное рабочее приложение находится в `example/`. Запуск:

```bash
python -m example.composite.bot
```

### `example/interfaces/bot/resources.py`

```python
import falcon
from pybotx import Bot, IncomingMessage, UnverifiedRequestError
from pybotx.bot.api.responses.command_accepted import build_command_accepted_response
from pybotx.bot.api.responses.unverified_request import build_unverified_request_response

class CommandResource:
    def __init__(self, bot: Bot):
        self._bot = bot
    
    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        try:
            bot_command = self._bot.parse_bot_command(
                req.media,
                request_headers=dict(req.headers),
            )
        except UnverifiedRequestError:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response()
            return

        if isinstance(bot_command, IncomingMessage):
            # Автоматическая диспетчеризация в handlers
            self._bot.dispatch_command(bot_command)

        resp.media = build_command_accepted_response()

class StatusResource:
    def __init__(self, bot: Bot):
        self._bot = bot
    
    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        try:
            resp.media = self._bot.get_raw_status(
                dict(req.params),
                request_headers=dict(req.headers),
            )
        except UnverifiedRequestError:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response()

class CallbackResource:
    def __init__(self, bot: Bot):
        self._bot = bot
    
    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        try:
            self._bot.parse_callback(req.media, request_headers=dict(req.headers))
        except UnverifiedRequestError:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response()
            return
        resp.media = {"status": "ok"}
```

### `example/composite/bot.py`

```python
import falcon
from waitress import serve
from pybotx import Bot, BotAccountWithSecret, BotMenu, CommandHandler
from example.app.usecases.echo import EchoUseCase
from example.interfaces.bot.resources import CommandResource, StatusResource, CallbackResource

# UseCases
echo = EchoUseCase()

# Bot
bot = Bot(
    bot_accounts=[
        BotAccountWithSecret(
            id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            cts_url="https://cts.example.com",
            secret_key="secret",
        )
    ],
    bot_menu=BotMenu({
        "/echo": "Вернуть сообщение обратно",
    }),
    handlers={
        "/echo": CommandHandler(echo),
    },
)

# Falcon app
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
        serve(application, host="0.0.0.0", port=8000)
    finally:
        bot.shutdown()
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
    bot.dispatch_command(bot_command)
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
| `handlers` | `dict[str, CommandHandler] \| None` | `{}` | Обработчики команд |
| `httpx_client` | `httpx.Client \| None` | новый клиент | Кастомный HTTP-клиент |
| `default_callback_timeout` | `float` | 60 с | Таймаут ожидания колбэка |
| `callback_repo` | `CallbackRepoProto \| None` | in-memory | Хранилище колбэков |
| `auth_version` | `BotXAuthVersion` | `V2` | Версия аутентификации |

## Аутентификация

| Версия | Описание |
|--------|----------|
| `BotXAuthVersion.V2` | JWT подписывается секретом бота, `iss` = UUID бота. Токен не нужен. |
| `BotXAuthVersion.V1` | Токен получается от BotX-сервера при `startup()`. |

**Как это работает:**

- **Bot** верифицирует входящие JWT запросы через `_verify_request()`
- **Client** добавляет Authorization header в исходящие запросы
- **BotAccountsStorage** — общий объект между Bot и Client, хранит аккаунты и секреты

## Client API

Client доступен через `bot.client` и предоставляет все методы для работы с BotX API.

### Отправка сообщений

```python
# Сообщение в чат (async, ждёт колбэк)
bot.client.send_message(bot_id=..., chat_id=..., body="текст")

# Сообщение без колбэка (BotX >= 3.58)
bot.client.send_message_sync(bot_id=..., chat_id=..., body="текст")

# Редактирование сообщения
bot.client.edit_message(bot_id=..., sync_id=..., body="новый текст")

# Ответ на сообщение
bot.client.reply_message(bot_id=..., sync_id=..., body="ответ")

# Удаление сообщения
bot.client.delete_message(bot_id=..., sync_id=...)
```

### Управление чатами

```python
# Создать чат
chat_id = bot.client.create_chat(
    bot_id=...,
    name="Новый чат",
    members=[user_huid1, user_huid2],
)

# Информация о чате
chat_info = bot.client.chat_info(bot_id=..., chat_id=...)

# Добавить пользователей
bot.client.add_users_to_chat(bot_id=..., chat_id=..., huids=[...])

# Удалить пользователей
bot.client.remove_users_from_chat(bot_id=..., chat_id=..., huids=[...])
```

### Поиск пользователей

```python
# По email
user = bot.client.search_user_by_email(bot_id=..., email="user@example.com")

# По HUID
user = bot.client.search_user_by_huid(bot_id=..., huid=...)

# По логину
user = bot.client.search_user_by_ad(bot_id=..., ad_login="user")
```

### Работа с файлами

```python
# Загрузить файл
from pathlib import Path

file = bot.client.upload_file(
    bot_id=...,
    chat_id=...,
    file_path=Path("document.pdf"),
)

# Скачать файл
content = bot.client.download_file(
    bot_id=...,
    file_id=...,
)
```

Полный список методов Client API см. в `pybotx/client/client.py`.

## Использование Client отдельно

Client можно использовать вне Bot для интеграций:

```python
from pybotx.client.client import Client
from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.callbacks.callback_manager import CallbackManager
from pybotx.bot.callbacks.callback_memory_repo import CallbackMemoryRepo
import httpx

# Создать зависимости
storage = BotAccountsStorage([bot_account])
httpx_client = httpx.Client()
callbacks_manager = CallbackManager(CallbackMemoryRepo())

# Создать Client
client = Client(
    bot_accounts_storage=storage,
    httpx_client=httpx_client,
    callbacks_manager=callbacks_manager,
)

# Использовать
client.send_message(bot_id=..., chat_id=..., body="текст")
```

## Миграция с предыдущей версии

### API методы перенесены в Client

**Было:**
```python
bot.send_message(bot_id=..., chat_id=..., body="текст")
bot.create_chat(bot_id=..., name="чат")
```

**Стало:**
```python
bot.client.send_message(bot_id=..., chat_id=..., body="текст")
bot.client.create_chat(bot_id=..., name="чат")
```

### Handlers вместо прямой диспетчеризации

**Было:**
```python
# Ручная маршрутизация в контроллере
if command == "/echo":
    result = echo_uc.execute(message.argument)
    bot.send_message(...)
```

**Стало:**
```python
# Автоматическая диспетчеризация через handlers
bot = Bot(
    handlers={
        "/echo": CommandHandler(echo_uc),
    },
)

# В resources
bot.dispatch_command(bot_command)
```

## Лицензия

MIT
