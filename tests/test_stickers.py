from collections.abc import Callable
from http import HTTPStatus
from tempfile import NamedTemporaryFile
from typing import IO, Any
from uuid import UUID

import httpx
import pytest
from respx.router import MockRouter

from pybotx import (
    Bot,
    BotAccountWithSecret,
    HandlerCollector,
    IncomingMessage,
    Sticker,
    lifespan_wrapper,
)

pytestmark = [pytest.mark.mock_authorization,
    pytest.mark.usefixtures("respx_mock"),
]

PNG_IMAGE = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00"
    b"\x00\x00%\xdbV\xca\x00\x00\x00\x03PLTE\x00\x00\x00\xa7z=\xda\x00"
    b"\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00\nIDAT\x08\xd7c`\x00"
    b"\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test__sticker__download(
    respx_mock: MockRouter,
    host: str,
    bot_account: BotAccountWithSecret,
    buffer: IO[bytes],
    api_incoming_message_factory: Callable[..., dict[str, Any]],
) -> None:
    # - Arrange -
    image_link = (
        f"https://{host}/uploads/sticker_pack/"
        "4ff8113b-8460-5977-86b2-c1798eb4fbce/"
        "14a762edf2e04c579de98098e22b01da.png"
    )

    endpoint = respx_mock.get(image_link).mock(
        return_value=httpx.Response(
            HTTPStatus.OK,
            content=PNG_IMAGE,
        ),
    )

    sticker = Sticker(
        id=UUID("4ff8113b-8460-5977-86b2-c1798eb4fbce"),
        emoji="🤔",
        image_link=image_link,
        pack_id=UUID("4ff8113b-8460-5977-86b2-c1798eb4fbce"),
    )

    payload = api_incoming_message_factory()

    collector = HandlerCollector()

    @collector.default_message_handler
    def default_handler(message: IncomingMessage, bot: Bot) -> None:
        sticker.download(buffer)

    built_bot = Bot(collectors=[collector], bot_accounts=[bot_account])

    # - Act -
    with lifespan_wrapper(built_bot) as bot:
        bot.execute_raw_bot_command(payload, verify_request=False)

    # - Assert -
    assert buffer.read() == PNG_IMAGE
    assert endpoint.called
