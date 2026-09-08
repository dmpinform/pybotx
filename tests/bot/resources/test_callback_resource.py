from typing import Any
from uuid import uuid4

import falcon
import falcon.testing

from pybotx import BotXAuthVersion, Callback
from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.resources.callback_resource import CallbackResource
from pybotx.models.method_callbacks import BotAPIMethodSuccessfulCallback


class _RecordingUseCase:
    def __init__(self) -> None:
        self.received: list[Any] = []

    def execute(self, message: Any) -> None:
        self.received.append(message)


def _build_app(bot_account: Any, callback: Callback) -> falcon.App:
    bot_accounts_storage = BotAccountsStorage(
        [bot_account],
        auth_version=BotXAuthVersion.V2,
    )
    app = falcon.App()
    app.add_route(
        "/notification/callback",
        CallbackResource(bot_accounts_storage, callback),
    )
    return app


def test__on_post__invalid_token__returns_401_with_non_empty_message(
    bot_account: Any,
) -> None:
    app = _build_app(bot_account, Callback(_RecordingUseCase()))

    result = falcon.testing.simulate_post(app, "/notification/callback", json={})

    assert result.status_code == 401
    assert result.json["error_data"]["status_message"]


def test__on_post__valid_callback__dispatches_to_callback_handler(
    bot_account: Any,
    authorization_header: dict[str, str],
) -> None:
    usecase = _RecordingUseCase()
    app = _build_app(bot_account, Callback(usecase))

    sync_id = uuid4()
    payload = {"sync_id": str(sync_id), "status": "ok", "result": {"foo": "bar"}}

    result = falcon.testing.simulate_post(
        app,
        "/notification/callback",
        json=payload,
        headers=authorization_header,
    )

    assert result.status_code == 200
    assert len(usecase.received) == 1
    received = usecase.received[0]
    assert isinstance(received, BotAPIMethodSuccessfulCallback)
    assert received.sync_id == sync_id
