from http import HTTPStatus
from tempfile import NamedTemporaryFile
from uuid import UUID

import httpx
import pytest
from respx.router import MockRouter

from pybotx import (
    Bot,
    BotAccountWithSecret,
    BubbleMarkup,
    EditMessage,
    HandlerCollector,
    KeyboardMarkup,
    MentionBuilder,
    OutgoingAttachment,
    lifespan_wrapper,
)

pytestmark = [pytest.mark.mock_authorization,
    pytest.mark.usefixtures("respx_mock"),
]


def test__edit_message__minimal_edit_succeed(
    respx_mock: MockRouter,
    host: str,
    bot_id: UUID,
    bot_account: BotAccountWithSecret,
) -> None:
    # - Arrange -
    endpoint = respx_mock.post(
        f"https://{host}/api/v3/botx/events/edit_event",
        headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
        json={
            "sync_id": "8ba66c5b-40bf-5c77-911d-519cb4e382e9",
        },
    ).mock(
        return_value=httpx.Response(
            HTTPStatus.ACCEPTED,
            json={
                "status": "ok",
                "result": "bot_command_result_pushed",
            },
        ),
    )

    built_bot = Bot(collectors=[HandlerCollector()], bot_accounts=[bot_account])

    # - Act -
    with lifespan_wrapper(built_bot) as bot:
        bot.edit_message(
            bot_id=bot_id,
            sync_id=UUID("8ba66c5b-40bf-5c77-911d-519cb4e382e9"),
        )

    # - Assert -
    assert endpoint.called


def test__edit_message__maximum_edit_succeed(
    respx_mock: MockRouter,
    host: str,
    bot_id: UUID,
    bot_account: BotAccountWithSecret,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # - Arrange -
    monkeypatch.setattr(
        "pybotx.models.message.mentions.uuid4",
        lambda: UUID("f3e176d5-ff46-4b18-b260-25008338c06e"),
    )

    endpoint = respx_mock.post(
        f"https://{host}/api/v3/botx/events/edit_event",
        headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
        json={
            "sync_id": "8ba66c5b-40bf-5c77-911d-519cb4e382e9",
            "payload": {
                "body": "@{mention:f3e176d5-ff46-4b18-b260-25008338c06e}!",
                "metadata": {"message": "metadata"},
                "bubble": [
                    [
                        {
                            "command": "/bubble-button",
                            "data": {},
                            "label": "Bubble button",
                            "opts": {"silent": True, "align": "center"},
                        },
                    ],
                ],
                "keyboard": [
                    [
                        {
                            "command": "/keyboard-button",
                            "data": {},
                            "label": "Keyboard button",
                            "opts": {"silent": True, "align": "center"},
                        },
                    ],
                ],
                "mentions": [
                    {
                        "mention_type": "user",
                        "mention_id": "f3e176d5-ff46-4b18-b260-25008338c06e",
                        "mention_data": {
                            "user_huid": "8f3abcc8-ba00-4c89-88e0-b786beb8ec24",
                        },
                    },
                ],
            },
            "file": {
                "file_name": "test.txt",
                "data": "data:text/plain;base64,SGVsbG8sIHdvcmxkIQo=",
            },
            "opts": {"raw_mentions": True},
        },
    ).mock(
        return_value=httpx.Response(
            HTTPStatus.ACCEPTED,
            json={
                "status": "ok",
                "result": "bot_command_result_pushed",
            },
        ),
    )

    built_bot = Bot(collectors=[HandlerCollector()], bot_accounts=[bot_account])

    bubbles = BubbleMarkup()
    bubbles.add_button(command="/bubble-button", label="Bubble button")

    keyboard = KeyboardMarkup()
    keyboard.add_button(command="/keyboard-button", label="Keyboard button")

    with NamedTemporaryFile("wb+") as buffer:
        buffer.write(b"Hello, world!\n")
        buffer.seek(0)

        file = OutgoingAttachment.from_buffer(buffer, "test.txt")

    # - Act -
    with lifespan_wrapper(built_bot) as bot:
        bot.edit_message(
            bot_id=bot_id,
            sync_id=UUID("8ba66c5b-40bf-5c77-911d-519cb4e382e9"),
            body=f"{MentionBuilder.user(UUID('8f3abcc8-ba00-4c89-88e0-b786beb8ec24'))}!",
            metadata={"message": "metadata"},
            bubbles=bubbles,
            keyboard=keyboard,
            file=file,
        )

    # - Assert -
    assert endpoint.called


def test__edit_message__clean_message_succeed(
    respx_mock: MockRouter,
    host: str,
    bot_id: UUID,
    bot_account: BotAccountWithSecret,
) -> None:
    # - Arrange -
    endpoint = respx_mock.post(
        f"https://{host}/api/v3/botx/events/edit_event",
        headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
        json={
            "payload": {
                "body": "",
                "metadata": {},
                "bubble": [],
                "keyboard": [],
                "mentions": [],
            },
            "sync_id": "8ba66c5b-40bf-5c77-911d-519cb4e382e9",
            "file": None,
        },
    ).mock(
        return_value=httpx.Response(
            HTTPStatus.ACCEPTED,
            json={
                "status": "ok",
                "result": "bot_command_result_pushed",
            },
        ),
    )

    built_bot = Bot(collectors=[HandlerCollector()], bot_accounts=[bot_account])

    # - Act -
    with lifespan_wrapper(built_bot) as bot:
        bot.edit_message(
            bot_id=bot_id,
            sync_id=UUID("8ba66c5b-40bf-5c77-911d-519cb4e382e9"),
            body="",
            metadata={},
            bubbles=BubbleMarkup(),
            keyboard=KeyboardMarkup(),
            file=None,
        )

    # - Assert -
    assert endpoint.called


def test__edit__succeed(
    respx_mock: MockRouter,
    host: str,
    bot_id: UUID,
    bot_account: BotAccountWithSecret,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # - Arrange -
    monkeypatch.setattr(
        "pybotx.models.message.mentions.uuid4",
        lambda: UUID("f3e176d5-ff46-4b18-b260-25008338c06e"),
    )

    endpoint = respx_mock.post(
        f"https://{host}/api/v3/botx/events/edit_event",
        headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
        json={
            "sync_id": "8ba66c5b-40bf-5c77-911d-519cb4e382e9",
            "payload": {
                "body": "@{mention:f3e176d5-ff46-4b18-b260-25008338c06e}!",
                "metadata": {"message": "metadata"},
                "bubble": [
                    [
                        {
                            "command": "/bubble-button",
                            "data": {},
                            "label": "Bubble button",
                            "opts": {"silent": True, "align": "center"},
                        },
                    ],
                ],
                "keyboard": [
                    [
                        {
                            "command": "/keyboard-button",
                            "data": {},
                            "label": "Keyboard button",
                            "opts": {"silent": True, "align": "center"},
                        },
                    ],
                ],
                "mentions": [
                    {
                        "mention_type": "user",
                        "mention_id": "f3e176d5-ff46-4b18-b260-25008338c06e",
                        "mention_data": {
                            "user_huid": "8f3abcc8-ba00-4c89-88e0-b786beb8ec24",
                        },
                    },
                ],
            },
            "file": {
                "file_name": "test.txt",
                "data": "data:text/plain;base64,SGVsbG8sIHdvcmxkIQo=",
            },
            "opts": {"raw_mentions": True},
        },
    ).mock(
        return_value=httpx.Response(
            HTTPStatus.ACCEPTED,
            json={
                "status": "ok",
                "result": "bot_command_result_pushed",
            },
        ),
    )

    built_bot = Bot(collectors=[HandlerCollector()], bot_accounts=[bot_account])

    bubbles = BubbleMarkup()
    bubbles.add_button(command="/bubble-button", label="Bubble button")

    keyboard = KeyboardMarkup()
    keyboard.add_button(command="/keyboard-button", label="Keyboard button")

    with NamedTemporaryFile("wb+") as buffer:
        buffer.write(b"Hello, world!\n")
        buffer.seek(0)

        file = OutgoingAttachment.from_buffer(buffer, "test.txt")

    message = EditMessage(
        bot_id=bot_id,
        sync_id=UUID("8ba66c5b-40bf-5c77-911d-519cb4e382e9"),
        body=f"{MentionBuilder.user(UUID('8f3abcc8-ba00-4c89-88e0-b786beb8ec24'))}!",
        metadata={"message": "metadata"},
        bubbles=bubbles,
        keyboard=keyboard,
        file=file,
    )

    # - Act -
    with lifespan_wrapper(built_bot) as bot:
        bot.edit(message=message)

    # - Assert -
    assert endpoint.called
