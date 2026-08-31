from http import HTTPStatus
from typing import Any
from uuid import UUID

import pytest
from respx.router import MockRouter

from pybotx import UserFromSearch, UserNotFoundError
from pybotx.client.exceptions.http import (
    InvalidBotXResponsePayloadError,
    InvalidBotXStatusCodeError,
)
from tests.testkit import BotXRequest, error_payload, mock_botx, ok_payload

pytestmark = [pytest.mark.mock_authorization,
    pytest.mark.usefixtures("respx_mock"),
]


def test__search_user_by_email_post__user_not_found_error_raised(
    respx_mock: MockRouter,
    host: str,
    bot_id: UUID,
    bot_factory: Any,
) -> None:
    # - Arrange -
    request = BotXRequest(
        method="POST",
        path="/api/v3/botx/users/by_email",
        json={"emails": ["ad_user@cts.com"]},
    )
    endpoint = mock_botx(
        respx_mock,
        host,
        request,
        error_payload("user_not_found"),
        HTTPStatus.NOT_FOUND,
    )

    # - Act -
    with bot_factory() as bot, pytest.raises(UserNotFoundError) as exc:
        bot.search_user_by_email_post(
            bot_id=bot_id,
            email="ad_user@cts.com",
        )

    # - Assert -
    assert "user_not_found" in str(exc.value)
    assert endpoint.called


def test__search_user_by_email_post__succeed(
    respx_mock: MockRouter,
    host: str,
    bot_id: UUID,
    user_from_search_with_data: UserFromSearch,
    user_from_search_with_data_json: dict[str, Any],
    bot_factory: Any,
) -> None:
    # - Arrange -
    request = BotXRequest(
        method="POST",
        path="/api/v3/botx/users/by_email",
        json={"emails": ["ad_user@cts.com"]},
    )
    endpoint = mock_botx(
        respx_mock,
        host,
        request,
        ok_payload([user_from_search_with_data_json]),
        HTTPStatus.OK,
    )

    # - Act -
    with bot_factory() as bot:
        user = bot.search_user_by_email_post(
            bot_id=bot_id,
            email="ad_user@cts.com",
        )

    # - Assert -
    assert user == user_from_search_with_data
    assert endpoint.called


def test__search_user_by_email_post_without_extra_data__succeed(
    respx_mock: MockRouter,
    host: str,
    bot_id: UUID,
    user_from_search_without_data: UserFromSearch,
    user_from_search_without_data_json: dict[str, Any],
    bot_factory: Any,
) -> None:
    # - Arrange -
    request = BotXRequest(
        method="POST",
        path="/api/v3/botx/users/by_email",
        json={"emails": ["ad_user@cts.com"]},
    )
    endpoint = mock_botx(
        respx_mock,
        host,
        request,
        ok_payload([user_from_search_without_data_json]),
        HTTPStatus.OK,
    )

    # - Act -
    with bot_factory() as bot:
        user = bot.search_user_by_email_post(
            bot_id=bot_id,
            email="ad_user@cts.com",
        )

    # - Assert -
    assert user == user_from_search_without_data
    assert endpoint.called


def test__search_user_by_email_post__list_response_logs_warning(
    respx_mock: MockRouter,
    host: str,
    bot_id: UUID,
    user_from_search_with_data_json: dict[str, Any],
    bot_factory: Any,
    loguru_caplog: pytest.LogCaptureFixture,
) -> None:
    request = BotXRequest(
        method="POST",
        path="/api/v3/botx/users/by_email",
        json={"emails": ["ad_user@cts.com"]},
    )
    endpoint = mock_botx(
        respx_mock,
        host,
        request,
        ok_payload([user_from_search_with_data_json, user_from_search_with_data_json]),
        HTTPStatus.OK,
    )

    with bot_factory() as bot:
        bot.search_user_by_email_post(
            bot_id=bot_id,
            email="ad_user@cts.com",
        )

    assert "multiple users" in loguru_caplog.text
    assert endpoint.called


def test__search_user_by_email_post__non_400_status_is_not_retried(
    respx_mock: MockRouter,
    host: str,
    bot_id: UUID,
    bot_factory: Any,
) -> None:
    request = BotXRequest(
        method="POST",
        path="/api/v3/botx/users/by_email",
        json={"emails": ["ad_user@cts.com"]},
    )
    endpoint = mock_botx(
        respx_mock,
        host,
        request,
        error_payload("unexpected_error"),
        HTTPStatus.INTERNAL_SERVER_ERROR,
    )

    with bot_factory() as bot, pytest.raises(InvalidBotXStatusCodeError):
        bot.search_user_by_email_post(
            bot_id=bot_id,
            email="ad_user@cts.com",
        )

    assert endpoint.called


def test__search_user_by_email_post__empty_list_raises_user_not_found(
    respx_mock: MockRouter,
    host: str,
    bot_id: UUID,
    bot_factory: Any,
) -> None:
    request = BotXRequest(
        method="POST",
        path="/api/v3/botx/users/by_email",
        json={"emails": ["ad_user@cts.com"]},
    )
    endpoint = mock_botx(
        respx_mock,
        host,
        request,
        ok_payload([]),
        HTTPStatus.OK,
    )

    with bot_factory() as bot, pytest.raises(UserNotFoundError):
        bot.search_user_by_email_post(
            bot_id=bot_id,
            email="ad_user@cts.com",
        )

    assert endpoint.called


def test__search_user_by_email_post__invalid_payload_raises_invalid_response(
    respx_mock: MockRouter,
    host: str,
    bot_id: UUID,
    user_from_search_with_data_json: dict[str, Any],
    bot_factory: Any,
) -> None:
    request = BotXRequest(
        method="POST",
        path="/api/v3/botx/users/by_email",
        json={"emails": ["ad_user@cts.com"]},
    )
    endpoint = mock_botx(
        respx_mock,
        host,
        request,
        ok_payload(user_from_search_with_data_json),
        HTTPStatus.OK,
    )

    with bot_factory() as bot, pytest.raises(InvalidBotXResponsePayloadError):
        bot.search_user_by_email_post(
            bot_id=bot_id,
            email="ad_user@cts.com",
        )

    assert endpoint.called
