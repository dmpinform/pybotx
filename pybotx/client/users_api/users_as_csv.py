from pybotx.buffer import BufferWritable
from pybotx.client.authorized_botx_method import AuthorizedBotXMethod
from pybotx.client.botx_method import response_exception_thrower
from pybotx.client.exceptions.users import NoUserKindSelectedError
from pybotx.models.api_base import UnverifiedPayloadBaseModel


class BotXAPIUsersAsCSVRequestPayload(UnverifiedPayloadBaseModel):
    cts_user: bool
    unregistered: bool
    botx: bool

    @classmethod
    def from_domain(
        cls,
        cts_user: bool,
        unregistered: bool,
        botx: bool,
    ) -> "BotXAPIUsersAsCSVRequestPayload":
        return cls(
            cts_user=cts_user,
            unregistered=unregistered,
            botx=botx,
        )


class UsersAsCSVMethod(AuthorizedBotXMethod):
    status_handlers = {
        **AuthorizedBotXMethod.status_handlers,
        400: response_exception_thrower(NoUserKindSelectedError),
    }

    def execute(
        self,
        payload: BotXAPIUsersAsCSVRequestPayload,
        buffer: BufferWritable,
    ) -> None:
        path = "/api/v3/botx/users/users_as_csv"

        with self._botx_method_stream(
            "GET",
            self._build_url(path),
            params=payload.jsonable_dict(),
        ) as response:
            # https://github.com/nedbat/coveragepy/issues/1223
            for chunk in response.iter_bytes():  # pragma: no branch
                buffer.write(chunk)
