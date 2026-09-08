"""Status resource for handling bot menu requests."""

from typing import Any

import falcon
from pydantic import ValidationError

from pybotx.bot.api.responses.unverified_request import (
    build_unverified_request_response,
)
from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.exceptions import UnverifiedRequestError
from pybotx.bot.resources.base_resource import BaseResource
from pybotx.logger import logger, pformat_jsonable_obj
from pybotx.models.status import (
    BotAPIStatusRecipient,
    BotMenu,
    build_bot_status_response,
)


class StatusResource(BaseResource):
    """GET /status — меню бота."""

    def __init__(
        self,
        bot_accounts_storage: BotAccountsStorage,
        bot_menu: BotMenu | None = None,
        verify_requests: bool = True,
    ) -> None:
        """Initialize status resource.

        :param bot_accounts_storage: BotAccountsStorage instance.
        :param bot_menu: Bot menu configuration.
        :param verify_requests: Enable JWT verification.
        """
        super().__init__(bot_accounts_storage, verify_requests)
        self._bot_menu = bot_menu or BotMenu({})

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle GET /status request.

        :param req: Falcon request.
        :param resp: Falcon response.
        """
        try:
            status = self._get_status(
                {
                    key: value if isinstance(value, str) else value[0]
                    for key, value in req.params.items()
                },
                {key.lower(): value for key, value in req.headers.items()},
            )
        except UnverifiedRequestError as exc:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response(str(exc))
            return

        resp.media = status

    def _get_status(
        self,
        query_params: dict[str, str],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Build status response.

        :param query_params: Query string parameters.
        :param headers: HTTP headers for verification.

        :return: Status response dict.
        :raises UnverifiedRequestError: If verification fails.
        :raises ValueError: If validation fails.
        """
        logger.opt(lazy=True).debug(
            "Got status: {status}",
            status=lambda: pformat_jsonable_obj(query_params),
        )

        # Verify request
        bot_account = self._verify_request(headers)

        # Parse status request
        try:
            bot_api_status_recipient = BotAPIStatusRecipient.model_validate(
                query_params
            )
        except ValidationError as exc:
            raise ValueError("Status request validation error") from exc

        status_recipient = bot_api_status_recipient.to_domain()

        # Verify bot_id matches
        if status_recipient.bot_id != bot_account.id:
            raise UnverifiedRequestError(
                f"Bot ID mismatch: token={bot_account.id}, status={status_recipient.bot_id}"
            )

        return build_bot_status_response(self._bot_menu)
