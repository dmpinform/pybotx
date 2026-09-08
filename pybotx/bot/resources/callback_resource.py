"""Callback resource for handling async results from BotX API."""

from typing import Any

import falcon
from pydantic import TypeAdapter

from pybotx.bot.api.responses.unverified_request import (
    build_unverified_request_response,
)
from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.callback import Callback
from pybotx.bot.exceptions import UnverifiedRequestError
from pybotx.bot.resources.base_resource import BaseResource
from pybotx.logger import logger
from pybotx.models.method_callbacks import BotXMethodCallback


class CallbackResource(BaseResource):
    """POST /notification/callback — async-результаты от BotX."""

    def __init__(
        self,
        bot_accounts_storage: BotAccountsStorage,
        callback: Callback,
        verify_requests: bool = True,
    ) -> None:
        """Initialize callback resource.

        :param bot_accounts_storage: BotAccountsStorage instance.
        :param callback: Callback handler to process incoming callbacks.
        :param verify_requests: Enable JWT verification.
        """
        super().__init__(bot_accounts_storage, verify_requests)
        self._callback = callback

    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle POST /notification/callback request.

        :param req: Falcon request.
        :param resp: Falcon response.
        """
        try:
            callback_msg = self._parse_callback(
                req.media,
                {key.lower(): value for key, value in req.headers.items()},
            )
        except UnverifiedRequestError as exc:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response(str(exc))
            return

        # Вызвать обработчик колбэка
        self._callback.execute(
            callback_msg,
        )

        resp.media = {"status": "ok"}

    def _parse_callback(
        self,
        raw_callback: dict[str, Any],
        headers: dict[str, str],
    ) -> BotXMethodCallback:
        """Parse raw callback into domain object.

        :param raw_callback: Raw JSON dict from BotX.
        :param headers: HTTP headers for verification.

        :return: BotXMethodCallback (success or error).
        :raises UnverifiedRequestError: If verification fails.
        """
        logger.debug("Got callback: {callback}", callback=raw_callback)

        # Verify request
        self._verify_request(headers)

        # Parse callback
        callback: BotXMethodCallback = TypeAdapter(BotXMethodCallback).validate_python(
            raw_callback,
        )

        return callback
