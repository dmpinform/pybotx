from uuid import UUID

import falcon
import falcon.testing
import urllib3

from pybotx import Callback, Client, Command, create_botx_app


class _StubUseCase:
    def execute(self, message: object) -> None:
        pass


def test__create_botx_app__wires_command_notification_status_routes(
    bot_id: UUID,
    cts_url: str,
) -> None:
    client = Client(
        bot_id=bot_id,
        cts_url=cts_url,
        secret_key="bee001bee001bee001bee001bee001bee001",
        http_client=urllib3.PoolManager(),
    )
    app = create_botx_app(
        client=client,
        commands={"/echo": Command(_StubUseCase())},
        callback=Callback(_StubUseCase()),
    )

    assert isinstance(app, falcon.App)

    result = falcon.testing.simulate_post(app, "/command", json={})
    assert result.status_code != 404

    result = falcon.testing.simulate_post(app, "/notification/callback", json={})
    assert result.status_code != 404

    result = falcon.testing.simulate_get(app, "/status")
    assert result.status_code != 404


def test__create_botx_app__shares_bot_accounts_storage_with_client(
    bot_id: UUID,
    cts_url: str,
) -> None:
    client = Client(
        bot_id=bot_id,
        cts_url=cts_url,
        secret_key="bee001bee001bee001bee001bee001bee001",
        http_client=urllib3.PoolManager(),
    )
    client.bot_accounts_storage.set_token(bot_id, "cached-token")

    create_botx_app(
        client=client,
        commands={},
        callback=Callback(_StubUseCase()),
    )

    assert client.bot_accounts_storage.get_token_or_none(bot_id) == "cached-token"
