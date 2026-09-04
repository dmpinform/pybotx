import json
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from json.decoder import JSONDecodeError
from typing import (
    Any,
    NoReturn,
    TypeVar,
)
from urllib.parse import urlencode
from uuid import UUID

import urllib3
from mypy_extensions import Arg
from pydantic import ValidationError

from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.callbacks.callback_manager import CallbackManager
from pybotx.client.exceptions.base import BaseClientError
from pybotx.client.exceptions.callbacks import BotXMethodFailedCallbackReceivedError
from pybotx.client.exceptions.http import (
    InvalidBotXResponsePayloadError,
    InvalidBotXStatusCodeError,
)
from pybotx.logger import logger, pformat_jsonable_obj, trim_file_data_in_outgoing_json
from pybotx.models.api_base import VerifiedPayloadBaseModel
from pybotx.models.method_callbacks import (
    BotAPIMethodFailedCallback,
    BotXMethodCallback,
)

StatusHandler = Callable[[Arg(urllib3.HTTPResponse, "response")], NoReturn]
StatusHandlers = Mapping[int, StatusHandler]

CallbackExceptionHandler = Callable[
    [Arg(BotAPIMethodFailedCallback, "callback")],
    NoReturn,
]
ErrorCallbackHandlers = Mapping[str, CallbackExceptionHandler]
TBotXAPIModel = TypeVar("TBotXAPIModel", bound=VerifiedPayloadBaseModel)


def response_exception_thrower(
    exc: type[BaseClientError],
    comment: str | None = None,
) -> StatusHandler:
    def factory(response: urllib3.HTTPResponse) -> NoReturn:
        raise exc.from_response(response, comment)

    return factory


def callback_exception_thrower(
    exc: type[BaseClientError],
    comment: str | None = None,
) -> CallbackExceptionHandler:
    def factory(callback: BotAPIMethodFailedCallback) -> NoReturn:
        raise exc.from_callback(callback, comment)

    return factory


class BotXMethod:
    status_handlers: StatusHandlers = {}
    error_callback_handlers: ErrorCallbackHandlers = {}

    def __init__(
        self,
        sender_bot_id: UUID,
        http_client: urllib3.PoolManager,
        bot_accounts_storage: BotAccountsStorage,
        callbacks_manager: CallbackManager | None = None,
    ) -> None:
        self._bot_id = sender_bot_id
        self._http_client = http_client
        self._bot_accounts_storage = bot_accounts_storage
        self._callbacks_manager = callbacks_manager

    # For MyPy checks
    execute: Callable[..., Any]

    def execute(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore
        raise NotImplementedError("You should define `execute` method")

    def _build_url(self, path: str) -> str:
        cts_url = self._bot_accounts_storage.get_cts_url(self._bot_id)
        return "/".join(part.strip("/") for part in (cts_url, path))

    def _verify_and_extract_api_model(
        self,
        model_cls: type[TBotXAPIModel],
        response: urllib3.HTTPResponse,
    ) -> TBotXAPIModel:
        try:
            raw_model = json.loads(response.data)
        except JSONDecodeError as decoding_exc:
            raise InvalidBotXResponsePayloadError(response) from decoding_exc

        logger.opt(lazy=True).debug(
            "Got response from pybotx: {json}",
            json=lambda: pformat_jsonable_obj(raw_model),
        )

        try:
            api_model = model_cls.model_validate(raw_model)
        except ValidationError as validation_exc:
            raise InvalidBotXResponsePayloadError(response) from validation_exc

        return api_model

    def _botx_method_call(self, *args: Any, **kwargs: Any) -> urllib3.HTTPResponse:
        self._log_outgoing_request(*args, **kwargs)

        method, url = args
        headers = kwargs.get("headers", {})
        json_data = kwargs.get("json")
        params = kwargs.get("params")

        # Добавить query params к URL
        if params:
            url = f"{url}?{urlencode(params)}"

        # Подготовить body и headers для JSON
        body = None
        if json_data is not None:
            body = json.dumps(json_data)
            headers = {**headers, "Content-Type": "application/json"}

        response = self._http_client.request(
            method,
            url,
            body=body,
            headers=headers,
            preload_content=True,  # Загружать content сразу
        )

        self._raise_for_status(response)
        return response

    @contextmanager
    def _botx_method_stream(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Iterator[urllib3.HTTPResponse]:
        self._log_outgoing_request(*args, **kwargs)

        method, url = args
        headers = kwargs.get("headers", {})
        json_data = kwargs.get("json")
        params = kwargs.get("params")

        if params:
            url = f"{url}?{urlencode(params)}"

        body = None
        if json_data is not None:
            body = json.dumps(json_data)
            headers = {**headers, "Content-Type": "application/json"}

        response = self._http_client.request(
            method,
            url,
            body=body,
            headers=headers,
            preload_content=False,  # Streaming mode
        )

        try:
            self._raise_for_status(response)
            yield response
        finally:
            response.release_conn()

    def _raise_for_status(self, response: urllib3.HTTPResponse) -> None:
        handler = self.status_handlers.get(response.status)
        if handler:
            handler(response)  # Handler should raise an exception

        # Проверить статус код (2xx = успех)
        if not (200 <= response.status < 300):
            raise InvalidBotXStatusCodeError(response)

    def _process_callback(
        self,
        sync_id: UUID,
        wait_callback: bool,
        callback_timeout: float | None,
        default_callback_timeout: float,
    ) -> BotXMethodCallback | None:
        assert self._callbacks_manager is not None, (
            "CallbackManager hasn't been passed to this method"
        )

        self._callbacks_manager.register_expected_callback(sync_id)
        self._callbacks_manager.create_botx_method_callback(sync_id)

        if callback_timeout is None:
            callback_timeout = default_callback_timeout

        if not wait_callback:
            self._callbacks_manager.setup_callback_timeout_alarm(
                sync_id,
                callback_timeout,
            )
            return None

        callback = self._callbacks_manager.wait_botx_method_callback(
            sync_id,
            callback_timeout,
        )

        if callback.status == "error":
            error_handler = self.error_callback_handlers.get(callback.reason)
            if not error_handler:
                raise BotXMethodFailedCallbackReceivedError(callback)

            error_handler(callback)  # Handler should raise an exception

        return callback

    def _log_outgoing_request(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        method, url = args
        query_params = kwargs.get("params")
        json_body = kwargs.get("json")

        log_template = "Performing request to BotX:\n{method} {url}"
        if query_params:
            log_template += "\nquery: {params}"
        if json_body is not None:
            log_template += "\njson: {json}"

        logger.opt(lazy=True).debug(
            log_template,
            method=lambda: method,  # If `lazy` enabled, all kwargs should be callable
            url=lambda: url,  # If `lazy` enabled, all kwargs should be callable
            params=lambda: pformat_jsonable_obj(query_params),
            json=lambda: pformat_jsonable_obj(
                trim_file_data_in_outgoing_json(json_body),
            ),
        )
