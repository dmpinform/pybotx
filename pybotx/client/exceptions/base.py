
import urllib3

from pybotx.models.method_callbacks import BotAPIMethodFailedCallback


class BaseClientError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)

    @classmethod
    def from_response(
        cls,
        response: urllib3.HTTPResponse,
        comment: str | None = None,
    ) -> "BaseClientError":
        # urllib3.HTTPResponse не хранит request, используем доступные атрибуты
        method = getattr(response, "_method", "UNKNOWN")
        url = response.geturl()
        status_code = response.status
        content = response.data

        message = (
            f"{method} {url}\n"
            f"failed with code {status_code} and payload:\n"
            f"{content!r}"
        )

        if comment is not None:
            message = f"{message}\n\nComment: {comment}"

        return cls(message)

    @classmethod
    def from_callback(
        cls,
        callback: BotAPIMethodFailedCallback,
        comment: str | None = None,
    ) -> "BaseClientError":
        message = (
            f"BotX method call with sync_id `{callback.sync_id!s}` "
            f"failed with: {callback}"
        )

        if comment is not None:
            message = f"{message}\n\nComment: {comment}"

        return cls(message)
