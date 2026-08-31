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
    HandlerCollector,
    KeyboardMarkup,
    MentionBuilder,
    OutgoingAttachment,
    ReplyMessage,
    lifespan_wrapper,
)

pytestmark = [pytest.mark.mock_authorization,
    pytest.mark.usefixtures("respx_mock"),
]


def test__reply_message__minimal_filled_reply_succeed(
    respx_mock: MockRouter,
    host: str,
    bot_id: UUID,
    bot_account: BotAccountWithSecret,
) -> None:
    # - Arrange -
    endpoint = respx_mock.post(
        f"https://{host}/api/v3/botx/events/reply_event",
        headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
        json={
            "source_sync_id": "8ba66c5b-40bf-5c77-911d-519cb4e382e9",
            "reply": {
                "status": "ok",
                "body": "Replied",
            },
            "opts": {"raw_mentions": True},
        },
    ).mock(
        return_value=httpx.Response(
            HTTPStatus.ACCEPTED,
            json={
                "status": "ok",
                "result": "bot_reply_pushed",
            },
        ),
    )

    built_bot = Bot(collectors=[HandlerCollector()], bot_accounts=[bot_account])

    # - Act -
    with lifespan_wrapper(built_bot) as bot:
        bot.reply_message(
            bot_id=bot_id,
            sync_id=UUID("8ba66c5b-40bf-5c77-911d-519cb4e382e9"),
            body="Replied",
        )

    # - Assert -
    assert endpoint.called


def test__reply_message__maximum_filled_reply_succeed(
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
        f"https://{host}/api/v3/botx/events/reply_event",
        headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
        json={
            "source_sync_id": "8ba66c5b-40bf-5c77-911d-519cb4e382e9",
            "reply": {
                "status": "ok",
                "body": "@{mention:f3e176d5-ff46-4b18-b260-25008338c06e}!",
                "metadata": {"message": "metadata"},
                "opts": {
                    "buttons_auto_adjust": True,
                    "silent_response": True,
                },
                "bubble": [
                    [
                        {
                            "command": "/bubble-button",
                            "label": "Bubble button",
                            "data": {},
                            "opts": {"silent": True, "align": "center"},
                        },
                    ],
                ],
                "keyboard": [
                    [
                        {
                            "command": "/keyboard-button",
                            "label": "Keyboard button",
                            "data": {},
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
            "opts": {
                "raw_mentions": True,
                "stealth_mode": True,
                "notification_opts": {"send": True, "force_dnd": True},
            },
        },
    ).mock(
        return_value=httpx.Response(
            HTTPStatus.ACCEPTED,
            json={
                "status": "ok",
                "result": "bot_reply_pushed",
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
        bot.reply_message(
            bot_id=bot_id,
            sync_id=UUID("8ba66c5b-40bf-5c77-911d-519cb4e382e9"),
            body=f"{MentionBuilder.user(UUID('8f3abcc8-ba00-4c89-88e0-b786beb8ec24'))}!",
            metadata={"message": "metadata"},
            bubbles=bubbles,
            keyboard=keyboard,
            file=file,
            silent_response=True,
            markup_auto_adjust=True,
            stealth_mode=True,
            send_push=True,
            ignore_mute=True,
        )

    # - Assert -
    assert endpoint.called


def test__reply__succeed(
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
        f"https://{host}/api/v3/botx/events/reply_event",
        headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
        json={
            "source_sync_id": "8ba66c5b-40bf-5c77-911d-519cb4e382e9",
            "reply": {
                "status": "ok",
                "body": "@{mention:f3e176d5-ff46-4b18-b260-25008338c06e}!",
                "metadata": {"message": "metadata"},
                "opts": {
                    "buttons_auto_adjust": True,
                    "silent_response": True,
                },
                "bubble": [
                    [
                        {
                            "command": "/bubble-button",
                            "label": "Bubble button",
                            "data": {},
                            "opts": {"silent": True, "align": "center"},
                        },
                    ],
                ],
                "keyboard": [
                    [
                        {
                            "command": "/keyboard-button",
                            "label": "Keyboard button",
                            "data": {},
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
            "opts": {
                "raw_mentions": True,
                "stealth_mode": True,
                "notification_opts": {"send": True, "force_dnd": True},
            },
        },
    ).mock(
        return_value=httpx.Response(
            HTTPStatus.ACCEPTED,
            json={
                "status": "ok",
                "result": "bot_reply_pushed",
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

    message = ReplyMessage(
        bot_id=bot_id,
        sync_id=UUID("8ba66c5b-40bf-5c77-911d-519cb4e382e9"),
        body=f"{MentionBuilder.user(UUID('8f3abcc8-ba00-4c89-88e0-b786beb8ec24'))}!",
        metadata={"message": "metadata"},
        bubbles=bubbles,
        keyboard=keyboard,
        file=file,
        silent_response=True,
        markup_auto_adjust=True,
        stealth_mode=True,
        send_push=True,
        ignore_mute=True,
    )
    # - Act -
    with lifespan_wrapper(built_bot) as bot:
        bot.reply(message=message)

    # - Assert -
    assert endpoint.called
