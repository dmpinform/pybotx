# pybotx

Синхронная Python-библиотека для работы с BotX API.

Библиотека отвечает за три вещи: разбор входящих команд, формирование исходящих запросов к BotX и верификацию подписей. Маршрутизация HTTP-запросов, DI и запуск сервера остаются на стороне приложения.

## Установка

```bash
pip install pybotx
```

## Архитектура

- **`Client`** — синхронный HTTP-клиент (на `urllib3`) для запросов к BotX API (сообщения, чаты, файлы, пользователи и т.д.). Хранит `BotAccountsStorage` — аккаунты бота и кэш токенов авторизации.
- **`create_botx_app(...)`** — фабрика, собирающая Falcon WSGI-приложение с тремя эндпоинтами (`/command`, `/status`, `/notification/callback`). Принимает уже созданный `Client` и переиспользует его `BotAccountsStorage`, чтобы не заводить второй, несинхронизированный кэш токенов.
- **`Command`/`Callback`** — тонкие обёртки, которые получают разобранный `IncomingMessage`/callback от Falcon-ресурса и передают его в юзкейс приложения (`usecase.execute(message)`). Маршрутизация к конкретному юзкейсу, доступ к `Client` и формирование ответа — ответственность самого юзкейса, а не библиотеки.

```
                    BotX API
                       │ HTTP
                       ▼
              create_botx_app()            ┌──────────────────┐
       (Falcon WSGI: /command, /status,    │ BotAccountsStorage│
              /notification/callback)  ◄───┤  (shared cache)   │
                       │ dispatch           └─────────┬─────────┘
                       ▼                               │
               Command / Callback                      │
                       │ usecase.execute(message)       │
                       ▼                               │
                    UseCase  ───────────► Client ◄──────┘
                                      (DI, отправка ответа)
```

## Концепция

BotX общается с ботом через три HTTP-эндпоинта:

| Метод | Путь | Назначение |
|-------|------|------------|
| `POST` | `/command` | Входящие сообщения и системные события |
| `GET` | `/status` | Меню бота (список команд) |
| `POST` | `/notification/callback` | Async-результаты от BotX |

`create_botx_app()` регистрирует все три маршрута в Falcon-приложении. Запускать это WSGI-приложение (например, через `waitress.serve`) и связывать всё вместе (создавать `Client`, юзкейсы, `Command`/`Callback`) — задача composite root приложения, см. `example/`.

## Быстрый старт

### 1. Создать `Client`

```python
from uuid import UUID

import urllib3

from pybotx import Client

client = Client(
    bot_id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
    cts_url="https://cts.example.com",
    secret_key="your-secret-key",
    http_client=urllib3.PoolManager(),
    # auth_version=BotXAuthVersion.V2,  # по умолчанию
)
```

### 2. Написать юзкейс

Юзкейс получает `Client` через DI-конструктор и весь `IncomingMessage` в `execute` — этого достаточно, чтобы прочитать аргументы команды (`message.argument`) и ответить в тот же чат (`message.bot.id`/`message.chat.id`):

```python
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
```

### 3. Обернуть в `Command`/`Callback` и собрать приложение

```python
from pybotx import Callback, Command, create_botx_app

echo = EchoUseCase(client)

application = create_botx_app(
    client=client,
    commands={"/echo": Command(echo)},
    callback=Callback(handle_callback_usecase),
)
```

### 4. Запустить

```python
from waitress import serve

serve(application, host="0.0.0.0", port=8000)
```

## `Command`/`Callback`

`Command(usecase)` и `Callback(usecase)` — единственная обязанность которых — вызвать `usecase.execute(message)` с тем сообщением/callback'ом, что разобрал и провалидировал Falcon-ресурс. Юзкейс сам решает, что делать: отправить ответ через `Client`, записать в БД, опубликовать событие и т.д.

Если нужна нестандартная логика диспетчеризации (например, отправить дополнительное подтверждение в чат), наследуйте `Command`:

```python
from pybotx import Client, Command
from pybotx.models.commands import BotCommand


class SendMailCommand(Command):
    def __init__(self, usecase, client: Client) -> None:
        super().__init__(usecase)
        self._client = client

    def execute(self, message: BotCommand) -> None:
        result = self._usecase.run(message)
        self._client.send_message(
            bot_id=message.bot.id,
            chat_id=message.chat.id,
            body=f"Email sent: {result}",
        )
```

### Паттерн «Наблюдатель» для фоновых уведомлений

Когда юзкейс не должен напрямую зависеть от `Client` (например, отправка уведомления может прийти не только из команды бота, но и из другого канала), используйте `classic.signals.Hub`: юзкейс публикует сигнал, а подписчик (`Receivers`) отправляет сообщение через `Client`. Пример — `example/app/usecases/notify.py` + `example/interfaces/bot/receivers.py`: `Notify.execute` кладёт `bot_id`/`chat_id` реального входящего сообщения в `Notification`, а `Receivers` только достаёт их из уведомления — без захардкоженных констант.

## `create_botx_app`

```python
def create_botx_app(
    client: Client,
    commands: dict[str, Command],
    callback: Callback,
    events: dict[type, Command] | None = None,
    bot_menu: BotMenu | None = None,
    verify_requests: bool = True,
) -> falcon.App:
    ...
```

| Параметр | Описание |
|----------|----------|
| `client` | Уже созданный `Client`; его `BotAccountsStorage` переиспользуется для верификации входящих JWT. |
| `commands` | Команды пользователя (`/echo`, `/help`, ...) → `Command`. |
| `callback` | Обработчик async-результатов BotX (`/notification/callback`). |
| `events` | Системные события (`ChatCreatedEvent`, `AddedToChatEvent`, ...) → `Command`, см. ниже. |
| `bot_menu` | Меню для `/status` (по умолчанию пустое). |
| `verify_requests` | Отключение верификации JWT (для тестов). |

## Системные события

`/command` может получать не только `IncomingMessage`, но и системные события (`ChatCreatedEvent`, `AddedToChatEvent`, `DeletedFromChatEvent` и другие из `pybotx.models.system_events`). Регистрируются они так же, как и обычные команды — через словарь `type → Command`, только ключ — класс события:

```python
from pybotx import ChatCreatedEvent, Command, create_botx_app

application = create_botx_app(
    client=client,
    commands={"/echo": Command(echo)},
    callback=Callback(handle_callback),
    events={ChatCreatedEvent: Command(on_chat_created_usecase)},
)
```

Юзкейс, зарегистрированный в `events`, получает в `execute()` соответствующий объект события вместо `IncomingMessage`.

## Пример приложения

Полностью собранное приложение — composite root, юзкейсы, кастомный `Command`, паттерн «Наблюдатель» — находится в `example/`. Это канонический референс того, как использовать библиотеку в реальном проекте. Запуск:

```bash
python -m example.composite.bot
```

Структура:
- `example/composite/bot.py` — точка сборки: создаёт `Client`, юзкейсы, `Command`/`Callback`, вызывает `create_botx_app`, запускает `waitress.serve`.
- `example/app/usecases/` — юзкейсы (`EchoUseCase`, `Notify`, `SendMail`, `HandleCallback`).
- `example/interfaces/bot/` — кастомный `Command` (`SendMailCommand`) и подписчик паттерна «Наблюдатель» (`Receivers`).

## Аутентификация

| Версия | Описание |
|--------|----------|
| `BotXAuthVersion.V2` (по умолчанию) | JWT подписывается секретом бота, `iss` = UUID бота. Токен от сервера не нужен. |
| `BotXAuthVersion.V1` | Токен запрашивается у BotX-сервера лениво, при первом исходящем запросе, и кэшируется в `BotAccountsStorage`. |

`create_botx_app` верифицирует входящие JWT-запросы к `/command`, `/status`, `/notification/callback` через общий с `Client` `BotAccountsStorage`. `Client` добавляет `Authorization`-заголовок к исходящим запросам.

## Client API

Полный список методов — в `pybotx/client/client.py`. Основные группы:

```python
# Сообщения
client.send_message(bot_id=..., chat_id=..., body="текст")
client.send_message_sync(bot_id=..., chat_id=..., body="текст")  # BotX >= 3.58, без callback
client.edit_message(bot_id=..., sync_id=..., body="новый текст")
client.reply_message(bot_id=..., sync_id=..., body="ответ")

# Чаты
client.create_chat(bot_id=..., name="Новый чат", members=[...])
client.chat_info(bot_id=..., chat_id=...)
client.add_users_to_chat(bot_id=..., chat_id=..., huids=[...])

# Пользователи
client.search_user_by_email(bot_id=..., email="user@example.com")
client.search_user_by_huid(bot_id=..., huid=...)

# Файлы
client.upload_file(bot_id=..., chat_id=..., file_path=Path("document.pdf"))
client.download_file(bot_id=..., file_id=...)
```

## Обработка ошибок

Все ошибки клиента наследуются от `BaseClientError` (`pybotx.client.exceptions`). Отдельно стоит `BotXNetworkError` — сетевые ошибки/таймауты транспорта (`urllib3.exceptions.HTTPError`), обёрнутые в единую иерархию, и `InvalidBotXStatusCodeError`/`InvalidBotXResponsePayloadError` — невалидный статус-код или тело ответа BotX.

## Миграция с версии на `Bot`/`HandlerCollector`/httpx

Более старая версия библиотеки предоставляла асинхронный `Bot` с встроенным HTTP-клиентом на `httpx`, диспетчеризацией через `HandlerCollector`/`CommandHandler` и жизненным циклом `bot.startup()`/`bot.shutdown()`. Начиная с этой версии:

- библиотека синхронная, транспорт — `urllib3.PoolManager`, который приложение создаёт и владеет сам;
- `Bot` заменён на пару `Client` (исходящие запросы) + `create_botx_app` (входящие Falcon-эндпоинты) — они делят один `BotAccountsStorage`, но не связаны друг с другом напрямую;
- `HandlerCollector`/`CommandHandler` заменены на явные словари `commands`/`events`, передаваемые в `create_botx_app`, и тонкие обёртки `Command`/`Callback` над юзкейсами приложения;
- `bot.startup()`/`bot.shutdown()` больше не нужны — токен для `BotXAuthVersion.V1` запрашивается лениво при первом исходящем запросе, а `http_client` закрывается приложением (`http_client.clear()`) при выходе.

## Лицензия

MIT
