"""Factory для создания Falcon WSGI приложения с BotX ресурсами."""

from typing import Any

import falcon

from pybotx import BotAccountWithSecret
from pybotx.auth import BotXAuthVersion
from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.resources.callback_resource import CallbackResource
from pybotx.bot.resources.command_resource import CommandResource
from pybotx.bot.resources.status_resource import StatusResource
from pybotx.models.status import BotMenu


def create_botx_app(
    bot_id: UUID,
    cts_url: str,
    secret_key: str,
    commands: dict[str, Any],
    callback: Any,
    auth_version: str = BotXAuthVersion.V2,
    bot_menu: BotMenu | None = None,
    verify_requests: bool = True,
) -> falcon.App:
    """Create Falcon WSGI app with BotX resources.

    :param credentials: BotAccountsStorage instance.
    :param client: Client instance for API calls.
    :param command_handlers: Dict mapping command strings to Command handlers.
                            Example: {"/echo": Command(EchoUseCase())}
    :param bot_menu: Bot menu for /status endpoint (optional).
    :param callback_handler: Optional handler function for incoming callbacks.
    :param verify_requests: Enable JWT verification.

    :return: Configured Falcon app.
    """
    credentials = BotAccountsStorage(
        [
            BotAccountWithSecret(
                id=bot_id,
                cts_url=cts_url,
                secret_key=secret_key,
            )
        ],
        auth_version=auth_version,
    )

    app = falcon.App()

    # Add routes
    app.add_route(
        "/command",
        CommandResource(
            credentials,
            commands,
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
