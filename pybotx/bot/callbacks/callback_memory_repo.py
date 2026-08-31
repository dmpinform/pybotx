import threading
from dataclasses import dataclass, field
from uuid import UUID

from pybotx.bot.callbacks.callback_repo_proto import CallbackRepoProto
from pybotx.bot.exceptions import BotShuttingDownError, BotXMethodCallbackNotFoundError
from pybotx.client.exceptions.callbacks import CallbackNotReceivedError
from pybotx.models.method_callbacks import BotXMethodCallback


@dataclass
class CallbackSlot:
    event: threading.Event = field(default_factory=threading.Event)
    result: BotXMethodCallback | None = None
    error: BotShuttingDownError | None = None


class CallbackMemoryRepo(CallbackRepoProto):
    def __init__(self) -> None:
        self._callback_slots: dict[UUID, CallbackSlot] = {}
        self._lock = threading.Lock()

    def create_botx_method_callback(self, sync_id: UUID) -> None:
        with self._lock:
            self._callback_slots[sync_id] = CallbackSlot()

    def set_botx_method_callback_result(
        self,
        callback: BotXMethodCallback,
    ) -> None:
        sync_id = callback.sync_id

        slot = self._get_botx_method_callback(sync_id)
        with self._lock:
            slot.result = callback
            slot.event.set()

    def wait_botx_method_callback(
        self,
        sync_id: UUID,
        timeout: float,
    ) -> BotXMethodCallback:
        slot = self._get_botx_method_callback(sync_id)

        if not slot.event.wait(timeout):
            with self._lock:
                self._callback_slots.pop(sync_id, None)
            raise CallbackNotReceivedError(sync_id)

        if slot.error is not None:
            raise slot.error

        assert slot.result is not None
        return slot.result

    def pop_botx_method_callback(
        self,
        sync_id: UUID,
    ) -> CallbackSlot:
        with self._lock:
            return self._callback_slots.pop(sync_id)

    def stop_callbacks_waiting(self) -> None:
        with self._lock:
            for sync_id, slot in self._callback_slots.items():
                if not slot.event.is_set():
                    slot.error = BotShuttingDownError(
                        f"Callback with sync_id `{sync_id!s}` can't be received",
                    )
                    slot.event.set()
            self._callback_slots.clear()

    def _get_botx_method_callback(self, sync_id: UUID) -> CallbackSlot:
        try:
            return self._callback_slots[sync_id]
        except KeyError:
            raise BotXMethodCallbackNotFoundError(sync_id) from None