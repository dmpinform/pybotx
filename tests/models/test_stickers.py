import io
from typing import Any
from uuid import uuid4

import pytest
import urllib3

from pybotx import InvalidBotXStatusCodeError
from pybotx.models.stickers import Sticker


class _FakeHTTPClient:
    def __init__(self, response: urllib3.HTTPResponse) -> None:
        self._response = response

    def request(self, method: str, url: str, **kwargs: Any) -> urllib3.HTTPResponse:
        return self._response


def _sticker() -> Sticker:
    return Sticker(
        id=uuid4(),
        emoji="😀",
        image_link="https://cts.example.com/sticker.png",
        pack_id=uuid4(),
    )


def test__sticker_download__writes_response_data_to_buffer() -> None:
    fake_client = _FakeHTTPClient(
        urllib3.HTTPResponse(body=b"image-bytes", status=200, preload_content=True),
    )
    buffer = io.BytesIO()

    _sticker().download(buffer, http_client=fake_client)  # type: ignore[arg-type]

    assert buffer.getvalue() == b"image-bytes"


def test__sticker_download__bad_status__raises_invalid_botx_status_code_error() -> None:
    fake_client = _FakeHTTPClient(
        urllib3.HTTPResponse(body=b"not found", status=404, preload_content=True),
    )
    buffer = io.BytesIO()

    with pytest.raises(InvalidBotXStatusCodeError):
        _sticker().download(buffer, http_client=fake_client)  # type: ignore[arg-type]
