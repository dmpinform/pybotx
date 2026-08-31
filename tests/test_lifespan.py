from collections.abc import Callable
from unittest.mock import Mock

import pytest
from respx.router import MockRouter

from pybotx import (
    Bot,
    BotAccountWithSecret,
    BotXAuthVersion,
    HandlerCollector,
    IncomingMessage,
)
from pybotx.bot.testing import lifespan_wrapper

pytestmark = [pytest.mark.mock_authorization,
    pytest.mark.usefixtures("respx_mock"),
]


def test__execute_bot_command__wait_for_task_execution(
    incoming_message_factory: Callable[..., IncomingMessage],
    correct_handler_trigger: Mock,
    bot_account: BotAccountWithSecret,
) -> None:
    # - Arrange -
    user_command = incoming_message_factory(body="/command")
    collector = HandlerCollector()

    @collector.command("/command", description="My command")
    def handler(message: IncomingMessage, bot: Bot) -> None:
        correct_handler_trigger()

    bot = Bot(collectors=[collector], bot_accounts=[bot_account])

    # - Act -
    with lifespan_wrapper(bot):
        bot.execute_bot_command(user_command).join()

        # - Assert -
        correct_handler_trigger.assert_called_once()


def test__shutdown__wait_for_active_handlers(
    incoming_message_factory: Callable[..., IncomingMessage],
    correct_handler_trigger: Mock,
    bot_account: BotAccountWithSecret,
) -> None:
    # - Arrange -
    user_command = incoming_message_factory(body="/command")
    collector = HandlerCollector()

    @collector.command("/command", description="My command")
    def handler(message: IncomingMessage, bot: Bot) -> None:
        correct_handler_trigger()

    bot = Bot(collectors=[collector], bot_accounts=[bot_account])

    # - Act -
    bot.execute_bot_command(user_command)
    bot.shutdown()

    # - Assert -
    correct_handler_trigger.assert_called_once()


def test__fetch_tokens__skips_for_auth_v2(
    respx_mock: MockRouter,
    bot_account: BotAccountWithSecret,
) -> None:
    # - Arrange -
    collector = HandlerCollector()
    bot = Bot(
        collectors=[collector],
        bot_accounts=[bot_account],
        auth_version=BotXAuthVersion.V2,
    )

    # - Act -
    bot.fetch_tokens()

    # - Assert -
    assert len(respx_mock.calls) == 0

    # Cleanup
    bot.shutdown()
