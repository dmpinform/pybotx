from collections.abc import Callable

from pybotx import Command, IncomingMessage


class _RecordingUseCase:
    def __init__(self) -> None:
        self.received: list[IncomingMessage] = []

    def execute(self, message: IncomingMessage) -> None:
        self.received.append(message)


def test__command_execute__calls_usecase_with_same_message(
    incoming_message_factory: Callable[..., IncomingMessage],
) -> None:
    usecase = _RecordingUseCase()
    command = Command(usecase)
    message = incoming_message_factory(body="/echo hello")

    command.execute(message)

    assert usecase.received == [message]
