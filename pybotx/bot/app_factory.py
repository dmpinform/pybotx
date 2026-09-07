"""Factory для создания Falcon WSGI приложения с BotX ресурсами."""

from collections.abc import Callable
from typing import Any

import falcon

from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.dispatcher import CommandDispatcher
from pybotx.bot.resources.callback_resource import CallbackResource
from pybotx.bot.resources.command_resource import CommandResource
from pybotx.bot.resources.status_resource import StatusResource
from pybotx.client.client import Client
from pybotx.models.method_callbacks import BotXMethodCallback
from pybotx.models.status import BotMenu


def create_botx_app(
    credentials: BotAccountsStorage,
    client: Client,
    command_handlers: dict[str, Any],
    bot_menu: BotMenu | None = None,
    callback_handler: Callable[[BotXMethodCallback], None] | None = None,
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
    app = falcon.App()

    # Create dispatcher
    dispatcher = CommandDispatcher(command_handlers)

    # Add routes
    app.add_route(
        "/command",
        CommandResource(
            credentials,
            dispatcher,
            client,
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

    app.add_route(
        "/notification/callback",
        CallbackResource(
            credentials,
            callback_handler,
            verify_requests,
        ),
    )

    return app
