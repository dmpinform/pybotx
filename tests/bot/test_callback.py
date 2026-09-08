from uuid import uuid4

from pybotx import Callback
from pybotx.models.method_callbacks import BotAPIMethodSuccessfulCallback


class _RecordingUseCase:
    def __init__(self) -> None:
        self.received: list[BotAPIMethodSuccessfulCallback] = []

    def execute(self, message: BotAPIMethodSuccessfulCallback) -> None:
        self.received.append(message)


def test__callback_execute__calls_usecase_with_same_message() -> None:
    usecase = _RecordingUseCase()
    callback = Callback(usecase)
    message = BotAPIMethodSuccessfulCallback(
        sync_id=uuid4(),
        status="ok",
        result={},
    )

    callback.execute(message)

    assert usecase.received == [message]
