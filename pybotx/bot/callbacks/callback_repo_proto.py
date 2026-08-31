from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from pybotx.models.method_callbacks import BotXMethodCallback

if TYPE_CHECKING:
    from pybotx.bot.callbacks.callback_memory_repo import CallbackSlot


class CallbackRepoProto(Protocol):
    def create_botx_method_callback(
        self,
        sync_id: UUID,
    ) -> None: ...  # pragma: no cover

    def set_botx_method_callback_result(
        self,
        callback: BotXMethodCallback,
    ) -> None: ...  # pragma: no cover

    def wait_botx_method_callback(
        self,
        sync_id: UUID,
        timeout: float,
    ) -> BotXMethodCallback: ...  # pragma: no cover

    def pop_botx_method_callback(
        self,
        sync_id: UUID,
    ) -> "CallbackSlot": ...  # pragma: no cover

    def stop_callbacks_waiting(self) -> None: ...  # pragma: no cover