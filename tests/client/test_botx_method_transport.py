import io
from typing import Any
from uuid import uuid4

import pytest
import urllib3

from pybotx import BotXNetworkError, InvalidBotXStatusCodeError
from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.client.botx_method import BotXMethod


class _FakeHTTPClient:
    def __init__(
        self,
        response: urllib3.HTTPResponse | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._response = response
        self._exc = exc
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> urllib3.HTTPResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response


def _fake_response(status: int = 200, data: bytes = b"{}") -> urllib3.HTTPResponse:
    return urllib3.HTTPResponse(body=data, status=status, preload_content=True)


def _build_method(http_client: Any) -> BotXMethod:
    return BotXMethod(
        sender_bot_id=uuid4(),
        http_client=http_client,
        bot_accounts_storage=BotAccountsStorage([]),
    )


def test__botx_method_call__with_json__builds_body_and_content_type_header() -> None:
    fake_client = _FakeHTTPClient(response=_fake_response())
    method = _build_method(fake_client)

    method._botx_method_call("POST", "https://cts.example.com/api", json={"a": 1})

    call = fake_client.calls[0]
    assert call["method"] == "POST"
    assert call["body"] == '{"a": 1}'
    assert call["headers"]["Content-Type"] == "application/json"
    assert "fields" not in call


def test__botx_method_call__with_fields__calls_request_with_fields_not_body() -> None:
    fake_client = _FakeHTTPClient(response=_fake_response())
    method = _build_method(fake_client)

    method._botx_method_call(
        "POST",
        "https://cts.example.com/upload",
        fields={"content": ("file.txt", b"data")},
    )

    call = fake_client.calls[0]
    assert call["fields"] == {"content": ("file.txt", b"data")}
    assert "body" not in call


def test__botx_method_stream__yields_response_that_can_be_streamed() -> None:
    streamable_response = urllib3.HTTPResponse(
        body=io.BytesIO(b"abcdef"),
        status=200,
        preload_content=False,
    )
    fake_client = _FakeHTTPClient(response=streamable_response)
    method = _build_method(fake_client)

    with method._botx_method_stream(
        "GET",
        "https://cts.example.com/download",
    ) as response:
        chunks = list(response.stream(amt=3))

    assert b"".join(chunks) == b"abcdef"


def test__botx_method_call__network_error__wraps_into_botx_network_error() -> None:
    network_exc = urllib3.exceptions.MaxRetryError(
        pool=None,  # type: ignore[arg-type]
        url="https://cts.example.com/api",
        reason=None,
    )
    fake_client = _FakeHTTPClient(exc=network_exc)
    method = _build_method(fake_client)

    with pytest.raises(BotXNetworkError) as exc_info:
        method._botx_method_call("GET", "https://cts.example.com/api")

    assert exc_info.value.cause is network_exc


def test__base_client_error_from_response__uses_real_http_method_not_unknown() -> None:
    fake_client = _FakeHTTPClient(response=_fake_response(status=500, data=b"oops"))
    method = _build_method(fake_client)

    with pytest.raises(InvalidBotXStatusCodeError) as exc_info:
        method._botx_method_call("GET", "https://cts.example.com/api")

    assert "GET" in str(exc_info.value)
    assert "UNKNOWN" not in str(exc_info.value)
