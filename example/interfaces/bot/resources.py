"""Falcon WSGI-ресурсы для трёх BotX-эндпоинтов."""

import falcon

from pybotx import Bot, IncomingMessage, UnverifiedRequestError
from pybotx.bot.api.responses.command_accepted import build_command_accepted_response
from pybotx.bot.api.responses.unverified_request import (
    build_unverified_request_response,
)


# возможно перейдет в бота с выбором фреймворка
class CommandResource:
    """POST /command — входящие сообщения и системные события."""

    def __init__(self, bot: Bot):
        self._bot = bot

    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        try:
            bot_command = self._bot.parse_bot_command(
                req.media,
                request_headers=dict(req.headers),
            )
        except UnverifiedRequestError:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response()
            return

        if isinstance(bot_command, IncomingMessage):
            self._bot.dispatch_command(bot_command)

        resp.media = build_command_accepted_response()


class StatusResource:
    """GET /status — меню бота."""

    def __init__(self, bot: Bot):
        self._bot = bot

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        try:
            status = self._bot.get_raw_status(
                dict(req.params),
                request_headers=dict(req.headers),
            )
        except UnverifiedRequestError:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response()
            return

        resp.media = status


class CallbackResource:
    """POST /notification/callback — async-результаты от BotX."""

    def __init__(self, bot: Bot):
        self._bot = bot

    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        try:
            self._bot.parse_callback(
                req.media,
                request_headers=dict(req.headers),
            )
        except UnverifiedRequestError:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response()
            return

        resp.media = {"status": "ok"}
