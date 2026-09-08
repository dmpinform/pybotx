from typing import Any
from uuid import UUID, uuid4

import falcon
import falcon.testing

from pybotx import BotXAuthVersion
from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.resources.status_resource import StatusResource
from pybotx.models.status import BotMenu


def _build_app(
    bot_account: Any,
    bot_menu: BotMenu | None = None,
) -> falcon.App:
    bot_accounts_storage = BotAccountsStorage(
        [bot_account],
        auth_version=BotXAuthVersion.V2,
    )
    app = falcon.App()
    app.add_route("/status", StatusResource(bot_accounts_storage, bot_menu))
    return app


def test__on_get__invalid_token__returns_401_with_non_empty_message(
    bot_account: Any,
) -> None:
    app = _build_app(bot_account)

    result = falcon.testing.simulate_get(app, "/status")

    assert result.status_code == 401
    assert result.json["error_data"]["status_message"]


def test__on_get__valid_token__returns_bot_menu(
    bot_id: UUID,
    bot_account: Any,
    authorization_header: dict[str, str],
) -> None:
    bot_menu = BotMenu({"/echo": "Echoes back the message"})
    app = _build_app(bot_account, bot_menu)

    result = falcon.testing.simulate_get(
        app,
        "/status",
        params={
            "bot_id": str(bot_id),
            "user_huid": str(uuid4()),
            "chat_type": "chat",
        },
        headers=authorization_header,
    )

    assert result.status_code == 200
    assert result.json["status"] == "ok"
    commands = result.json["result"]["commands"]
    assert commands == [
        {"description": "Echoes back the message", "body": "/echo", "name": "/echo"},
    ]


def test__on_get__bot_id_mismatch__returns_401(
    bot_account: Any,
    authorization_header: dict[str, str],
) -> None:
    app = _build_app(bot_account)

    result = falcon.testing.simulate_get(
        app,
        "/status",
        params={
            "bot_id": str(uuid4()),
            "user_huid": str(uuid4()),
            "chat_type": "chat",
        },
        headers=authorization_header,
    )

    assert result.status_code == 401
    assert result.json["error_data"]["status_message"]
