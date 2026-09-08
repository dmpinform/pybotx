from typing import Any

import urllib3

from pybotx.client.exceptions.base import BaseClientError


class InvalidBotXResponseError(BaseClientError):
    """Received invalid response."""

    def __init__(self, response: urllib3.BaseHTTPResponse) -> None:
        exc = BaseClientError.from_response(response)
        self.response = response

        self.args = exc.args

    def __reduce__(self) -> Any:
        # This method required to pass exception from pybotx logger to bot logger.
        return type(self), (self.response,)


class InvalidBotXStatusCodeError(InvalidBotXResponseError):
    """Received invalid status code."""


class InvalidBotXResponsePayloadError(InvalidBotXResponseError):
    """Received invalid status code."""


class BotXNetworkError(BaseClientError):
    """Не удалось выполнить запрос к BotX (сетевая ошибка/таймаут)."""

    def __init__(self, method: str, url: str, cause: Exception) -> None:
        self.method = method
        self.url = url
        self.cause = cause
        super().__init__(f"{method} {url}\nfailed with network error: {cause!r}")

    def __reduce__(self) -> Any:
        return type(self), (self.method, self.url, self.cause)
