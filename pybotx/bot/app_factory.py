"""Factory для создания Falcon WSGI приложения с BotX ресурсами."""

from typing import Any

import falcon

from pybotx.bot.resources.callback_resource import CallbackResource
from pybotx.bot.resources.command_resource import CommandResource
from pybotx.bot.resources.status_resource import StatusResource
from pybotx.client.client import Client
from pybotx.models.status import BotMenu


def create_botx_app(
    client: Client,
    commands: dict[str, Any],
    callback: Any,
    events: dict[type, Any] | None = None,
    bot_menu: BotMenu | None = None,
    verify_requests: bool = True,
) -> falcon.App[falcon.Request, falcon.Response]:
    """Create Falcon WSGI app with BotX resources.

    :param client: Client instance; its BotAccountsStorage is reused for
                    request verification, so auth tokens are cached once.
    :param commands: Dict mapping command strings to Command handlers.
                      Example: {"/echo": Command(EchoUseCase(client))}
    :param callback: Callback handler for incoming async results.
    :param events: Dict mapping system event types to Command handlers.
    :param bot_menu: Bot menu for /status endpoint (optional).
    :param verify_requests: Enable JWT verification.

    :return: Configured Falcon app.
    """
    credentials = client.bot_accounts_storage

    app = falcon.App()

    app.add_route(
        "/command",
        CommandResource(
            credentials,
            commands,
            events,
            verify_requests,
        ),
    )

    app.add_route(
        "/notification/callback",
        CallbackResource(
            credentials,
            callback,
            verify_requests,
        ),
    )

    app.add_route(
        "/status",
        StatusResource(
            credentials,
            bot_menu,
            verify_requests,
        ),
    )

    return app
