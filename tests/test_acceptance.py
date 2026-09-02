"""Acceptance tests for the simplified pybotx bot mechanism."""
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from pybotx import (
    Bot,
    BotAccountWithSecret,
    BotMenu,
    IncomingMessage,
    UnverifiedRequestError,
)
from example.app.bot_controller import BotController
from example.app.usecases.echo import EchoUseCase
from example.app.usecases.notify import NotifyUseCase


BOT_ID = UUID("24348246-6791-4ac0-9d86-b948cd6a0e46")
CTS_URL = "https://cts.example.com"
SECRET_KEY = "bee001bee001bee001bee001bee001bee001"


@pytest.fixture
def bot_account() -> BotAccountWithSecret:
    return BotAccountWithSecret(id=BOT_ID, cts_url=CTS_URL, secret_key=SECRET_KEY)


@pytest.fixture
def bot(bot_account: BotAccountWithSecret) -> Bot:
    return Bot(
        bot_accounts=[bot_account],
        bot_menu=BotMenu({"/echo": "Эхо", "/notify": "Уведомить"}),
    )


# ---------------------------------------------------------------------------
# parse_bot_command
# ---------------------------------------------------------------------------


def test__parse_bot_command__returns_incoming_message(
    bot: Bot,
    api_incoming_message_factory: Any,
    authorization_header: dict[str, str],
) -> None:
    raw = api_incoming_message_factory(body="/echo hello")

    result = bot.parse_bot_command(raw, request_headers=authorization_header)

    assert isinstance(result, IncomingMessage)
    assert result.body == "/echo hello"


def test__parse_bot_command__populates_bot_and_chat_ids(
    bot: Bot,
    api_incoming_message_factory: Any,
    authorization_header: dict[str, str],
) -> None:
    raw = api_incoming_message_factory(bot_id=BOT_ID)

    result = bot.parse_bot_command(raw, request_headers=authorization_header)

    assert isinstance(result, IncomingMessage)
    assert result.bot.id == BOT_ID


def test__parse_bot_command__raises_on_invalid_jwt(
    bot: Bot,
    api_incoming_message_factory: Any,
) -> None:
    raw = api_incoming_message_factory()
    bad_headers = {"authorization": "Bearer not_a_real_token"}

    with pytest.raises(UnverifiedRequestError):
        bot.parse_bot_command(raw, request_headers=bad_headers)


def test__parse_bot_command__raises_on_missing_auth_header(
    bot: Bot,
    api_incoming_message_factory: Any,
) -> None:
    raw = api_incoming_message_factory()

    with pytest.raises(UnverifiedRequestError):
        bot.parse_bot_command(raw, request_headers={})


def test__parse_bot_command__skips_verification_when_disabled(
    bot: Bot,
    api_incoming_message_factory: Any,
) -> None:
    raw = api_incoming_message_factory()

    result = bot.parse_bot_command(raw, verify_request=False)

    assert isinstance(result, IncomingMessage)


# ---------------------------------------------------------------------------
# get_raw_status
# ---------------------------------------------------------------------------


def test__get_raw_status__returns_menu_commands(
    bot: Bot,
    authorization_header: dict[str, str],
) -> None:
    params = {
        "bot_id": str(BOT_ID),
        "user_huid": "f16cdc5f-6366-5552-9ecd-c36290ab3d11",
        "chat_type": "chat",
    }

    status = bot.get_raw_status(params, request_headers=authorization_header)

    assert status["result"]["commands"]
    command_bodies = [c["body"] for c in status["result"]["commands"]]
    assert "/echo" in command_bodies
    assert "/notify" in command_bodies


def test__get_raw_status__raises_on_invalid_jwt(bot: Bot) -> None:
    params = {
        "bot_id": str(BOT_ID),
        "user_huid": "f16cdc5f-6366-5552-9ecd-c36290ab3d11",
        "chat_type": "chat",
    }
    bad_headers = {"authorization": "Bearer bad_token"}

    with pytest.raises(UnverifiedRequestError):
        bot.get_raw_status(params, request_headers=bad_headers)


# ---------------------------------------------------------------------------
# BotController dispatch
# ---------------------------------------------------------------------------


def test__bot_controller__echo_calls_send_message(
    bot: Bot,
    api_incoming_message_factory: Any,
    authorization_header: dict[str, str],
) -> None:
    echo_uc = EchoUseCase()
    notify_uc = NotifyUseCase()
    controller = BotController(bot=bot, echo_uc=echo_uc, notify_uc=notify_uc)

    raw = api_incoming_message_factory(body="/echo world")
    message = bot.parse_bot_command(raw, request_headers=authorization_header)
    assert isinstance(message, IncomingMessage)

    with patch.object(bot, "send_message") as mock_send:
        controller.dispatch(message)

    mock_send.assert_called_once()
    _, kwargs = mock_send.call_args
    assert kwargs["body"] == "world"


def test__bot_controller__unknown_command_is_ignored(
    bot: Bot,
    api_incoming_message_factory: Any,
    authorization_header: dict[str, str],
) -> None:
    controller = BotController(
        bot=bot,
        echo_uc=EchoUseCase(),
        notify_uc=NotifyUseCase(),
    )
    raw = api_incoming_message_factory(body="/unknown_cmd arg")
    message = bot.parse_bot_command(raw, request_headers=authorization_header)
    assert isinstance(message, IncomingMessage)

    with patch.object(bot, "send_message") as mock_send:
        controller.dispatch(message)

    mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# NotifyUseCase — observer pattern
# ---------------------------------------------------------------------------


def test__notify_use_case__calls_all_subscribers() -> None:
    uc = NotifyUseCase()
    handler1 = MagicMock()
    handler2 = MagicMock()

    uc.subscribe(handler1)
    uc.subscribe(handler2)
    uc.execute("hello")

    handler1.assert_called_once_with("hello")
    handler2.assert_called_once_with("hello")


def test__notify_use_case__no_subscribers_does_not_raise() -> None:
    uc = NotifyUseCase()
    uc.execute("hello")  # should not raise


def test__notify_use_case__bot_send_message_triggered(
    bot: Bot,
) -> None:
    uc = NotifyUseCase()
    chat_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    with patch.object(bot, "send_message") as mock_send:
        uc.subscribe(lambda text: bot.send_message(bot_id=BOT_ID, chat_id=chat_id, body=text))
        uc.execute("notification text")

    mock_send.assert_called_once_with(bot_id=BOT_ID, chat_id=chat_id, body="notification text")


# ---------------------------------------------------------------------------
# EchoUseCase
# ---------------------------------------------------------------------------


def test__echo_use_case__returns_input_unchanged() -> None:
    uc = EchoUseCase()
    assert uc.execute("test message") == "test message"


def test__echo_use_case__empty_string() -> None:
    uc = EchoUseCase()
    assert uc.execute("") == ""
