from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

import falcon
import falcon.testing

from pybotx import BotXAuthVersion, Command, IncomingMessage
from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.resources.command_resource import CommandResource
from pybotx.models.system_events.chat_created import ChatCreatedEvent


class _RecordingUseCase:
    def __init__(self) -> None:
        self.received: list[Any] = []

    def execute(self, message: Any) -> None:
        self.received.append(message)


def _build_app(
    bot_account: Any,
    commands: dict[str, Command] | None = None,
    events: dict[type, Command] | None = None,
) -> falcon.App:
    bot_accounts_storage = BotAccountsStorage(
        [bot_account],
        auth_version=BotXAuthVersion.V2,
    )
    app = falcon.App()
    app.add_route(
        "/command",
        CommandResource(bot_accounts_storage, commands or {}, events),
    )
    return app


def test__on_post__invalid_token__returns_401_with_non_empty_message(
    bot_account: Any,
) -> None:
    app = _build_app(bot_account)

    result = falcon.testing.simulate_post(app, "/command", json={})

    assert result.status_code == 401
    assert result.json["error_data"]["status_message"]


def test__on_post__valid_user_command__dispatches_to_registered_command(
    bot_id: UUID,
    bot_account: Any,
    authorization_header: dict[str, str],
    api_incoming_message_factory: Callable[..., dict[str, Any]],
) -> None:
    usecase = _RecordingUseCase()
    app = _build_app(bot_account, commands={"/echo": Command(usecase)})

    payload = api_incoming_message_factory(body="/echo hello", bot_id=bot_id)

    result = falcon.testing.simulate_post(
        app,
        "/command",
        json=payload,
        headers=authorization_header,
    )

    assert result.status_code == 200
    assert len(usecase.received) == 1
    assert isinstance(usecase.received[0], IncomingMessage)
    assert usecase.received[0].body == "/echo hello"


def test__on_post__valid_system_event__dispatches_to_registered_event_handler(
    bot_id: UUID,
    host: str,
    bot_account: Any,
    authorization_header: dict[str, str],
) -> None:
    usecase = _RecordingUseCase()
    app = _build_app(bot_account, events={ChatCreatedEvent: Command(usecase)})

    payload = {
        "bot_id": str(bot_id),
        "sync_id": str(uuid4()),
        "proto_version": 4,
        "command": {
            "command_type": "system",
            "body": "system:chat_created",
            "data": {
                "chat_type": "chat",
                "creator": str(uuid4()),
                "group_chat_id": str(uuid4()),
                "members": [
                    {
                        "admin": True,
                        "huid": str(uuid4()),
                        "name": "Bob",
                        "user_kind": "user",
                    },
                ],
                "name": "Test chat",
            },
        },
        "from": {
            "host": host,
            "group_chat_id": str(uuid4()),
            "chat_type": "chat",
        },
    }

    result = falcon.testing.simulate_post(
        app,
        "/command",
        json=payload,
        headers=authorization_header,
    )

    assert result.status_code == 200
    assert len(usecase.received) == 1
    assert isinstance(usecase.received[0], ChatCreatedEvent)


def test__on_post__bot_id_mismatch__returns_401(
    bot_account: Any,
    authorization_header: dict[str, str],
    api_incoming_message_factory: Callable[..., dict[str, Any]],
) -> None:
    app = _build_app(bot_account, commands={})

    payload = api_incoming_message_factory(body="/echo hello", bot_id=uuid4())

    result = falcon.testing.simulate_post(
        app,
        "/command",
        json=payload,
        headers=authorization_header,
    )

    assert result.status_code == 401
    assert result.json["error_data"]["status_message"]
