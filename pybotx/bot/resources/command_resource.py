"""Command resource for handling incoming messages and system events."""

from typing import TYPE_CHECKING, Any

import falcon
from pydantic import TypeAdapter, ValidationError

from pybotx.bot.api.responses.command_accepted import build_command_accepted_response
from pybotx.bot.api.responses.unverified_request import (
    build_unverified_request_response,
)
from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.exceptions import UnverifiedRequestError
from pybotx.bot.resources.base_resource import BaseResource
from pybotx.logger import log_incoming_request
from pybotx.models.commands import (
    BotAPIIncomingMessage,
    BotAPISystemEvent,
    BotCommand,
)
from pybotx.models.enums import BotAPICommandTypes
from pybotx.models.message.incoming_message import IncomingMessage

if TYPE_CHECKING:
    from pybotx.bot.dispatcher import CommandDispatcher
    from pybotx.client.client import Client


class CommandResource(BaseResource):
    """POST /command — входящие сообщения и системные события."""

    def __init__(
        self,
        bot_accounts_storage: BotAccountsStorage,
        dispatcher: "CommandDispatcher",
        client: "Client",
        verify_requests: bool = True,
        logging_commands: bool = True,
    ) -> None:
        """Initialize command resource.

        :param bot_accounts_storage: BotAccountsStorage instance.
        :param dispatcher: CommandDispatcher for routing commands.
        :param client: Client instance for API calls.
        :param verify_requests: Enable JWT verification.
        :param logging_commands: Enable command logging.
        """
        super().__init__(bot_accounts_storage, verify_requests)
        self._dispatcher = dispatcher
        self._client = client
        self._logging_commands = logging_commands

    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle POST /command request.

        :param req: Falcon request.
        :param resp: Falcon response.
        """
        try:
            bot_command = self._parse_command(
                req.media,
                dict(req.headers),
            )
        except UnverifiedRequestError:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response()
            return

        # Dispatch только IncomingMessage (user messages)
        if isinstance(bot_command, IncomingMessage):
            self._dispatcher.dispatch(bot_command, self._client)

        resp.media = build_command_accepted_response()

    def _parse_command(
        self,
        raw_command: dict[str, Any],
        headers: dict[str, str],
    ) -> BotCommand:
        """Parse raw command into domain object.

        :param raw_command: Raw JSON dict from BotX.
        :param headers: HTTP headers for verification.

        :return: BotCommand (IncomingMessage or SystemEvent).
        :raises UnverifiedRequestError: If verification fails.
        :raises ValueError: If validation fails.
        """
        if self._logging_commands:
            log_incoming_request(raw_command, message="Got command: ")

        # Verify request first
        bot_account = self._verify_request(headers)

        # Parse command
        try:
            command_type = raw_command.get("command", {}).get("command_type")
            if command_type == BotAPICommandTypes.USER:
                bot_api_command = BotAPIIncomingMessage.model_validate(raw_command)
            else:
                bot_api_command = TypeAdapter(BotAPISystemEvent).validate_python(
                    raw_command
                )
        except ValidationError as validation_exc:
            raise ValueError("Bot command validation error") from validation_exc

        bot_command = bot_api_command.to_domain(raw_command)

        # Verify bot_id matches
        if bot_command.bot.id != bot_account.id:
            raise UnverifiedRequestError(
                f"Bot ID mismatch: token={bot_account.id}, command={bot_command.bot.id}"
            )

        return bot_command
