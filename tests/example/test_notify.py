from collections.abc import Callable
from typing import Any
from uuid import UUID

from classic.signals import Hub

from example.app.usecases.notify import Notify
from example.interfaces.bot.receivers import Receivers
from pybotx import IncomingMessage


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def send_message(self, *, bot_id: UUID, chat_id: UUID, body: str) -> UUID:
        self.calls.append({"bot_id": bot_id, "chat_id": chat_id, "body": body})
        return chat_id


def test__notify__sends_to_bot_id_and_chat_id_of_incoming_message_not_hardcoded(
    incoming_message_factory: Callable[..., IncomingMessage],
) -> None:
    hub = Hub()
    client = _RecordingClient()
    Receivers(hub=hub, client=client)
    notify = Notify(hub)

    message = incoming_message_factory(body="/notify hello everyone")

    notify.execute(message)

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["bot_id"] == message.bot.id
    assert call["chat_id"] == message.chat.id
    assert call["body"] == "hello everyone"


def test__notify__different_messages_route_to_their_own_chat(
    incoming_message_factory: Callable[..., IncomingMessage],
) -> None:
    hub = Hub()
    client = _RecordingClient()
    Receivers(hub=hub, client=client)
    notify = Notify(hub)

    first_message = incoming_message_factory(body="/notify first")
    second_message = incoming_message_factory(body="/notify second")

    notify.execute(first_message)
    notify.execute(second_message)

    assert client.calls[0]["chat_id"] == first_message.chat.id
    assert client.calls[1]["chat_id"] == second_message.chat.id
    assert client.calls[0]["chat_id"] != client.calls[1]["chat_id"]
