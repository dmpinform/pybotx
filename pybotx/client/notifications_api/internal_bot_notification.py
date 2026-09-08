from typing import Any, Literal
from uuid import UUID

from pybotx.client.authorized_botx_method import AuthorizedBotXMethod
from pybotx.client.botx_method import response_exception_thrower
from pybotx.client.exceptions.common import RateLimitReachedError
from pybotx.missing import Missing, MissingOptional
from pybotx.models.api_base import UnverifiedPayloadBaseModel, VerifiedPayloadBaseModel


class BotXAPIInternalBotNotificationRequestPayload(UnverifiedPayloadBaseModel):
    group_chat_id: UUID
    data: dict[str, Any]
    opts: Missing[dict[str, Any]]
    recipients: MissingOptional[list[UUID]]

    @classmethod
    def from_domain(
        cls,
        chat_id: UUID,
        data: dict[str, Any],
        opts: Missing[dict[str, Any]],
        recipients: MissingOptional[list[UUID]],
    ) -> "BotXAPIInternalBotNotificationRequestPayload":
        return cls(
            group_chat_id=chat_id,
            data=data,
            opts=opts,
            recipients=recipients,
        )


class BotXAPISyncIdResult(VerifiedPayloadBaseModel):
    sync_id: UUID


class BotXAPIInternalBotNotificationResponsePayload(VerifiedPayloadBaseModel):
    status: Literal["ok"]
    result: BotXAPISyncIdResult

    def to_domain(self) -> UUID:
        return self.result.sync_id


class InternalBotNotificationMethod(AuthorizedBotXMethod):
    status_handlers = {
        **AuthorizedBotXMethod.status_handlers,
        429: response_exception_thrower(RateLimitReachedError),
    }

    def execute(
        self,
        payload: BotXAPIInternalBotNotificationRequestPayload,
    ) -> BotXAPIInternalBotNotificationResponsePayload:
        path = "/api/v4/botx/notifications/internal"

        response = self._botx_method_call(
            "POST",
            self._build_url(path),
            json=payload.jsonable_dict(),
        )
        api_model = self._verify_and_extract_api_model(
            BotXAPIInternalBotNotificationResponsePayload,
            response,
        )
        return api_model
