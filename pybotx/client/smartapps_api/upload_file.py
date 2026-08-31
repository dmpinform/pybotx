import tempfile
from typing import Literal

from pybotx.buffer import BufferReadable
from pybotx.client.authorized_botx_method import AuthorizedBotXMethod
from pybotx.client.botx_method import response_exception_thrower
from pybotx.client.exceptions.files import FileTypeNotAllowed
from pybotx.constants import CHUNK_SIZE
from pybotx.models.api_base import VerifiedPayloadBaseModel


class BotXAPIUploadFileResult(VerifiedPayloadBaseModel):
    link: str


class BotXAPIUploadFileResponsePayload(VerifiedPayloadBaseModel):
    result: BotXAPIUploadFileResult
    status: Literal["ok"]

    def to_domain(self) -> str:
        return self.result.link


class UploadFileMethod(AuthorizedBotXMethod):
    status_handlers = {
        **AuthorizedBotXMethod.status_handlers,
        400: response_exception_thrower(FileTypeNotAllowed),
    }

    def execute(
        self,
        buffer: BufferReadable,
        filename: str,
    ) -> BotXAPIUploadFileResponsePayload:
        path = "/api/v3/botx/smartapps/upload_file"

        with tempfile.SpooledTemporaryFile(max_size=CHUNK_SIZE) as tmp_file:
            chunk = buffer.read(CHUNK_SIZE)
            while chunk:
                tmp_file.write(chunk)
                chunk = buffer.read(CHUNK_SIZE)

            tmp_file.seek(0)

            response = self._botx_method_call(
                "POST",
                self._build_url(path),
                files={"content": (filename, tmp_file)},
            )

        return self._verify_and_extract_api_model(
            BotXAPIUploadFileResponsePayload,
            response,
        )
