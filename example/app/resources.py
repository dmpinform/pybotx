"""Falcon WSGI-ресурсы для трёх BotX-эндпоинтов."""
import falcon

from pybotx import IncomingMessage, UnverifiedRequestError
from pybotx.bot.api.responses.command_accepted import build_command_accepted_response
from pybotx.bot.api.responses.unverified_request import build_unverified_request_response

from example.app.deps import bot, controller


class CommandResource:
    """POST /command — входящие сообщения и системные события."""

    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        try:
            bot_command = bot.parse_bot_command(
                req.media,
                request_headers=dict(req.headers),
            )
        except UnverifiedRequestError:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response()
            return

        if isinstance(bot_command, IncomingMessage):
            controller.dispatch(bot_command)

        resp.media = build_command_accepted_response()


class StatusResource:
    """GET /status — меню бота."""

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        try:
            status = bot.get_raw_status(
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

    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        try:
            bot.parse_callback(
                req.media,
                request_headers=dict(req.headers),
            )
        except UnverifiedRequestError:
            resp.status = falcon.HTTP_401
            resp.media = build_unverified_request_response()
            return

        resp.media = {"status": "ok"}
