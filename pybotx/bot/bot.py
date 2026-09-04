from collections.abc import Iterator, Mapping, Sequence
from typing import Any
from uuid import UUID

import httpx
import jwt
from pydantic import TypeAdapter, ValidationError

from pybotx.auth import BotXAuthVersion
from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.callbacks.callback_manager import CallbackManager
from pybotx.bot.callbacks.callback_memory_repo import CallbackMemoryRepo
from pybotx.bot.callbacks.callback_repo_proto import CallbackRepoProto
from pybotx.bot.exceptions import (
    RequestHeadersNotProvidedError,
    UnknownBotAccountError,
    UnverifiedRequestError,
)
from pybotx.client.exceptions.common import InvalidBotAccountError
from pybotx.constants import BOTX_DEFAULT_TIMEOUT
from pybotx.logger import log_incoming_request, logger, pformat_jsonable_obj
from pybotx.models.bot_account import BotAccountWithSecret
from pybotx.models.commands import (
    BotAPIIncomingMessage,
    BotAPISystemEvent,
    BotCommand,
)
from pybotx.models.enums import BotAPICommandTypes
from pybotx.models.method_callbacks import BotXMethodCallback
from pybotx.models.status import (
    BotAPIStatusRecipient,
    BotMenu,
    build_bot_status_response,
)


class Bot:
    def __init__(
        self,
        *,
        bot_accounts: Sequence[BotAccountWithSecret],
        bot_menu: BotMenu | None = None,
        httpx_client: httpx.Client | None = None,
        default_callback_timeout: float = BOTX_DEFAULT_TIMEOUT,
        callback_repo: CallbackRepoProto | None = None,
        auth_version: BotXAuthVersion = BotXAuthVersion.V2,
        handlers: dict[str, Any] | None = None,
    ) -> None:
        if not bot_accounts:
            logger.warning("Bot has no bot accounts")

        self._bot_menu: BotMenu = bot_menu or BotMenu({})
        self._default_callback_timeout = default_callback_timeout
        self._bot_accounts_storage = BotAccountsStorage(
            list(bot_accounts),
            auth_version=auth_version,
        )
        self._httpx_client = httpx_client or httpx.Client()

        if not callback_repo:
            callback_repo = CallbackMemoryRepo()

        self._callbacks_manager = CallbackManager(callback_repo)

        # Создать Client instance
        from pybotx.client.client import Client

        self._client = Client(
            bot_accounts_storage=self._bot_accounts_storage,
            httpx_client=self._httpx_client,
            callbacks_manager=self._callbacks_manager,
            default_callback_timeout=self._default_callback_timeout,
        )

        # Сохранить handlers
        self._handlers = handlers or {}

    @property
    def client(self) -> Any:
        """Get Client instance for API calls.

        :return: Client instance.
        """
        return self._client

    def dispatch_command(self, message: Any) -> None:
        """Dispatch command to registered handler.

        :param message: IncomingMessage from BotX.
        """
        # Извлечь команду из тела сообщения (например, "/echo")
        command = message.body.split()[0] if message.body else ""

        # Найти handler для команды
        handler = self._handlers.get(command)

        # Вызвать handler если он существует
        if handler:
            handler.handle(message, self._client)

    def parse_bot_command(
        self,
        raw_bot_command: dict[str, Any],
        request_headers: Mapping[str, str] | None = None,
        verify_request: bool = True,
        logging_command: bool = True,
    ) -> BotCommand:
        """Parse raw incoming command into a domain object.

        :param raw_bot_command: Raw JSON dict from BotX.
        :param request_headers: HTTP headers for JWT verification.
        :param verify_request: Verify JWT signature.
        :param logging_command: Log the incoming command.

        :return: BotCommand (IncomingMessage or a SystemEvent subtype).
        """
        if logging_command:
            log_incoming_request(raw_bot_command, message="Got command: ")

        if verify_request:
            self._verify_request(request_headers)

        try:
            command_type = raw_bot_command.get("command", {}).get("command_type")
            if command_type == BotAPICommandTypes.USER:
                bot_api_command = BotAPIIncomingMessage.model_validate(raw_bot_command)
            else:
                bot_api_command = TypeAdapter(BotAPISystemEvent).validate_python(
                    raw_bot_command
                )
        except ValidationError as validation_exc:
            raise ValueError("Bot command validation error") from validation_exc

        bot_command = bot_api_command.to_domain(raw_bot_command)
        self._bot_accounts_storage.ensure_bot_id_exists(bot_command.bot.id)
        return bot_command

    def get_raw_status(
        self,
        query_params: dict[str, str],
        request_headers: Mapping[str, str] | None = None,
        verify_request: bool = True,
    ) -> dict[str, Any]:
        """Build status response for BotX server.

        :param query_params: Query string parameters from the request.
        :param request_headers: HTTP headers for JWT verification.
        :param verify_request: Verify JWT signature.

        :return: Status response dict ready to be serialized to JSON.
        """
        logger.opt(lazy=True).debug(
            "Got status: {status}",
            status=lambda: pformat_jsonable_obj(query_params),
        )

        if verify_request:
            self._verify_request(request_headers)

        try:
            bot_api_status_recipient = BotAPIStatusRecipient.model_validate(query_params)
        except ValidationError as exc:
            raise ValueError("Status request validation error") from exc

        status_recipient = bot_api_status_recipient.to_domain()
        self._bot_accounts_storage.ensure_bot_id_exists(status_recipient.bot_id)

        return build_bot_status_response(self._bot_menu)

    def parse_callback(
        self,
        raw_callback: dict[str, Any],
        request_headers: Mapping[str, str] | None = None,
        verify_request: bool = True,
    ) -> None:
        """Register async callback result received from BotX server.

        :param raw_callback: Raw JSON dict from BotX callback request.
        :param request_headers: HTTP headers for JWT verification.
        :param verify_request: Verify JWT signature.
        """
        logger.debug("Got callback: {callback}", callback=raw_callback)

        if verify_request:
            self._verify_request(request_headers)

        callback: BotXMethodCallback = TypeAdapter(BotXMethodCallback).validate_python(
            raw_callback,
        )

        self._callbacks_manager.set_botx_method_callback_result(callback)

    def wait_botx_method_callback(
        self,
        sync_id: UUID,
    ) -> BotXMethodCallback:
        timeout = self._callbacks_manager.cancel_callback_timeout_alarm(
            sync_id,
            return_remaining_time=True,
        )

        return self._callbacks_manager.wait_botx_method_callback(sync_id, timeout)

    @property
    def bot_accounts(self) -> Iterator[BotAccountWithSecret]:
        yield from self._bot_accounts_storage.iter_bot_accounts()

    def fetch_tokens(self) -> None:
        """Fetch tokens for all bot accounts (only for V1 auth)."""
        if self._bot_accounts_storage.get_auth_version() != BotXAuthVersion.V1:
            return
        for bot_account in self.bot_accounts:
            try:
                token = self._client.get_token(bot_id=bot_account.id)
            except (InvalidBotAccountError, httpx.HTTPError):
                logger.opt(exception=True).warning(
                    "Can't get token for bot account: "
                    f"host - {bot_account.host}, bot_id - {bot_account.id}",
                )
                continue

            self._bot_accounts_storage.set_token(bot_account.id, token)

    def startup(self, *, fetch_tokens: bool = True) -> None:
        if fetch_tokens:
            self.fetch_tokens()

    def shutdown(self) -> None:
        self._callbacks_manager.stop_callbacks_waiting()
        self._httpx_client.close()

    def _verify_request(
        self,
        headers: Mapping[str, str] | None,
        *,
        trusted_issuers: set[str] | None = None,
    ) -> None:
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
        if self._is_v2_payload(token_payload):
            self._verify_request_v2(token, token_payload, decode_algorithms)
        else:
            self._verify_request_v1(
                token,
                token_payload,
                decode_algorithms,
                trusted_issuers,
            )

    @staticmethod
    def _is_v2_payload(token_payload: Mapping[str, Any]) -> bool:
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
        self,
        token: str,
        token_payload: Mapping[str, Any],
        decode_algorithms: list[str],
    ) -> None:
        issuer = token_payload.get("iss")
        if issuer is None:
            raise UnverifiedRequestError('Token is missing the "iss" claim')
        if not isinstance(issuer, str):
            raise UnverifiedRequestError("Invalid issuer")

        try:
            bot_id = UUID(issuer)
        except (TypeError, ValueError) as exc:
            raise UnverifiedRequestError("Invalid issuer") from exc

        try:
            bot_account = self._bot_accounts_storage.get_bot_account(bot_id)
        except UnknownBotAccountError as unknown_bot_exc:
            raise UnverifiedRequestError(unknown_bot_exc.args[0]) from unknown_bot_exc

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

    def _verify_request_v1(
        self,
        token: str,
        token_payload: Mapping[str, Any],
        decode_algorithms: list[str],
        trusted_issuers: set[str] | None,
    ) -> None:
        audience = token_payload.get("aud")
        if (
            not audience
            or not isinstance(audience, Sequence)
            or isinstance(audience, str)
            or len(audience) != 1
        ):
            raise UnverifiedRequestError("Invalid audience parameter was provided.")

        try:
            bot_account = self._bot_accounts_storage.get_bot_account(UUID(audience[-1]))
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

