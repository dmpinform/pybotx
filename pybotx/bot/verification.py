"""JWT verification logic for BotX requests."""

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

import jwt

from pybotx.bot.exceptions import (
    RequestHeadersNotProvidedError,
    UnknownBotAccountError,
    UnverifiedRequestError,
)
from pybotx.models.bot_account import BotAccountWithSecret


def verify_request(
    headers: Mapping[str, str] | None,
    credentials: list[BotAccountWithSecret],
    *,
    trusted_issuers: set[str] | None = None,
) -> BotAccountWithSecret:
    """Verify JWT token and return matching bot account.

    :param headers: HTTP headers containing Authorization token.
    :param credentials: List of bot accounts to verify against.
    :param trusted_issuers: Trusted issuers for V1 auth (optional).

    :return: BotAccountWithSecret that matches the token.
    :raises RequestHeadersNotProvidedError: If headers are None.
    :raises UnverifiedRequestError: If token verification fails.
    """
    if headers is None:
        raise RequestHeadersNotProvidedError

    authorization_header = headers.get("authorization")
    if not authorization_header:
        raise UnverifiedRequestError("The authorization token was not provided.")

    token = authorization_header.split()[-1]
    decode_algorithms = ["HS256"]

    try:
        token_payload = jwt.decode(
            jwt=token,
            algorithms=decode_algorithms,
            options={
                "verify_signature": False,
            },
        )
    except jwt.DecodeError as decode_exc:
        raise UnverifiedRequestError(decode_exc.args[0]) from decode_exc

    if _is_v2_payload(token_payload):
        return _verify_request_v2(token, token_payload, decode_algorithms, credentials)
    else:
        return _verify_request_v1(
            token,
            token_payload,
            decode_algorithms,
            credentials,
            trusted_issuers,
        )


def _is_v2_payload(token_payload: Mapping[str, Any]) -> bool:
    """Check if token payload is V2 format.

    :param token_payload: Decoded JWT payload.
    :return: True if V2 format, False otherwise.
    """
    if token_payload.get("version") == 2:
        return True

    audience = token_payload.get("aud")
    issuer = token_payload.get("iss")
    if not isinstance(audience, str) or not isinstance(issuer, str):
        return False

    try:
        UUID(issuer)
    except (TypeError, ValueError):
        return False

    return True


def _verify_request_v2(
    token: str,
    token_payload: Mapping[str, Any],
    decode_algorithms: list[str],
    credentials: list[BotAccountWithSecret],
) -> BotAccountWithSecret:
    """Verify V2 JWT token.

    :param token: JWT token string.
    :param token_payload: Decoded JWT payload.
    :param decode_algorithms: Algorithms to use for decoding.
    :param credentials: List of bot accounts.

    :return: BotAccountWithSecret that matches the token.
    :raises UnverifiedRequestError: If verification fails.
    """
    issuer = token_payload.get("iss")
    if issuer is None:
        raise UnverifiedRequestError('Token is missing the "iss" claim')
    if not isinstance(issuer, str):
        raise UnverifiedRequestError("Invalid issuer")

    try:
        bot_id = UUID(issuer)
    except (TypeError, ValueError) as exc:
        raise UnverifiedRequestError("Invalid issuer") from exc

    # Find bot account by ID
    bot_account = _get_bot_account(bot_id, credentials)

    audience = token_payload.get("aud")
    if not audience or not isinstance(audience, str):
        raise UnverifiedRequestError("Invalid audience parameter was provided.")
    if audience != bot_account.host:
        raise UnverifiedRequestError("Invalid audience parameter was provided.")

    try:
        jwt.decode(
            jwt=token,
            key=bot_account.secret_key,
            algorithms=decode_algorithms,
            issuer=str(bot_account.id),
            audience=bot_account.host,
            leeway=1,
        )
    except jwt.InvalidTokenError as exc:
        raise UnverifiedRequestError(exc.args[0]) from exc

    return bot_account


def _verify_request_v1(
    token: str,
    token_payload: Mapping[str, Any],
    decode_algorithms: list[str],
    credentials: list[BotAccountWithSecret],
    trusted_issuers: set[str] | None,
) -> BotAccountWithSecret:
    """Verify V1 JWT token.

    :param token: JWT token string.
    :param token_payload: Decoded JWT payload.
    :param decode_algorithms: Algorithms to use for decoding.
    :param credentials: List of bot accounts.
    :param trusted_issuers: Trusted issuers (optional).

    :return: BotAccountWithSecret that matches the token.
    :raises UnverifiedRequestError: If verification fails.
    """
    audience = token_payload.get("aud")
    if (
        not audience
        or not isinstance(audience, Sequence)
        or isinstance(audience, str)
        or len(audience) != 1
    ):
        raise UnverifiedRequestError("Invalid audience parameter was provided.")

    try:
        bot_account = _get_bot_account(UUID(audience[-1]), credentials)
    except UnknownBotAccountError as unknown_bot_exc:
        raise UnverifiedRequestError(unknown_bot_exc.args[0]) from unknown_bot_exc

    try:
        jwt.decode(
            jwt=token,
            key=bot_account.secret_key,
            algorithms=decode_algorithms,
            issuer=bot_account.host,
            leeway=1,
            options={
                "verify_aud": False,
                "verify_iss": False,
            },
        )
    except jwt.InvalidTokenError as exc:
        raise UnverifiedRequestError(exc.args[0]) from exc

    issuer = token_payload.get("iss")
    if issuer is None:
        raise UnverifiedRequestError('Token is missing the "iss" claim')

    if issuer != bot_account.host:
        if not trusted_issuers or issuer not in trusted_issuers:
            raise UnverifiedRequestError("Invalid issuer")

    return bot_account


def _get_bot_account(
    bot_id: UUID,
    credentials: list[BotAccountWithSecret],
) -> BotAccountWithSecret:
    """Find bot account by ID.

    :param bot_id: Bot account ID to find.
    :param credentials: List of bot accounts.

    :return: BotAccountWithSecret with matching ID.
    :raises UnknownBotAccountError: If bot ID not found.
    """
    for bot_account in credentials:
        if bot_account.id == bot_id:
            return bot_account

    raise UnknownBotAccountError(bot_id)
