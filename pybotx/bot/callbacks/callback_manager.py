import threading
import time
from typing import Literal, NamedTuple, overload
from uuid import UUID

from pybotx.bot.callbacks.callback_repo_proto import CallbackRepoProto
from pybotx.bot.exceptions import BotXMethodCallbackNotFoundError
from pybotx.client.exceptions.callbacks import CallbackNotReceivedError
from pybotx.logger import logger
from pybotx.models.method_callbacks import BotXMethodCallback

ORPHAN_CALLBACK_TTL_SECONDS = 5.0
ORPHAN_PENDING_CALLBACKS_LIMIT = 1000


class CallbackAlarm(NamedTuple):
    alarm_time: float
    timer: threading.Timer


def _callback_timeout_alarm(
    callbacks_manager: "CallbackManager",
    sync_id: UUID,
    timeout: float,
) -> None:
    callbacks_manager.cancel_callback_timeout_alarm(sync_id)
    callbacks_manager.pop_botx_method_callback(sync_id)

    logger.error("Callback `{sync_id}` wasn't waited", sync_id=sync_id)


def _orphan_callback_alarm(
    callbacks_manager: "CallbackManager",
    sync_id: UUID,
    timeout: float,
) -> None:
    callbacks_manager.cancel_orphan_callback_alarm(sync_id)
    callbacks_manager.drop_orphan_callback(sync_id)

    logger.warning(
        "Callback `{sync_id}` received without a registered handler and expired",
        sync_id=sync_id,
    )


class CallbackManager:
    def __init__(self, callback_repo: CallbackRepoProto) -> None:
        self._callback_repo = callback_repo
        self._callback_alarms: dict[UUID, CallbackAlarm] = {}
        self._orphan_callback_alarms: dict[UUID, CallbackAlarm] = {}
        self._expected_sync_ids: set[UUID] = set()
        self._pending_callbacks: dict[UUID, BotXMethodCallback] = {}
        self._expired_sync_ids: set[UUID] = set()
        self._lock = threading.Lock()

    def register_expected_callback(self, sync_id: UUID) -> None:
        self._expected_sync_ids.add(sync_id)
        self.cancel_orphan_callback_alarm(sync_id)

    def create_botx_method_callback(self, sync_id: UUID) -> None:
        # Repo call is outside the lock: repo.create may block (e.g. on shutdown
        # hooks) while callback delivery must stay able to take the lock.
        self._callback_repo.create_botx_method_callback(sync_id)

        with self._lock:
            pending = self._pending_callbacks.pop(sync_id, None)
            self._expected_sync_ids.discard(sync_id)

        if pending is not None:
            self._callback_repo.set_botx_method_callback_result(pending)
            self.cancel_orphan_callback_alarm(sync_id)

    def set_botx_method_callback_result(
        self,
        callback: BotXMethodCallback,
    ) -> None:
        sync_id = callback.sync_id
        if sync_id in self._expired_sync_ids:
            raise BotXMethodCallbackNotFoundError(sync_id) from None
        try:
            self._callback_repo.set_botx_method_callback_result(callback)
        except BotXMethodCallbackNotFoundError:
            with self._lock:
                if sync_id in self._pending_callbacks:
                    self._pending_callbacks[sync_id] = callback
                    return
                if sync_id in self._expected_sync_ids:
                    self._pending_callbacks[sync_id] = callback
                    return
                if len(self._orphan_callback_alarms) >= ORPHAN_PENDING_CALLBACKS_LIMIT:
                    logger.warning(
                        "Pending callbacks limit reached; dropping orphan callback "
                        "`{sync_id}`",
                        sync_id=sync_id,
                    )
                    return
                self._pending_callbacks[sync_id] = callback
                self._setup_orphan_callback_alarm(sync_id, ORPHAN_CALLBACK_TTL_SECONDS)
            logger.warning(
                "Callback `{sync_id}` received without a registered handler; "
                "buffering",
                sync_id=sync_id,
            )

    def wait_botx_method_callback(
        self,
        sync_id: UUID,
        timeout: float,
    ) -> BotXMethodCallback:
        try:
            return self._callback_repo.wait_botx_method_callback(sync_id, timeout)
        except CallbackNotReceivedError:
            self._mark_callback_expired(sync_id)
            raise

    def pop_botx_method_callback(
        self,
        sync_id: UUID,
    ) -> object:
        return self._callback_repo.pop_botx_method_callback(sync_id)

    def stop_callbacks_waiting(self) -> None:
        self._callback_repo.stop_callbacks_waiting()

    def setup_callback_timeout_alarm(self, sync_id: UUID, timeout: float) -> None:
        timer = threading.Timer(
            timeout,
            _callback_timeout_alarm,
            args=(self, sync_id, timeout),
        )
        timer.daemon = True

        with self._lock:
            self._callback_alarms[sync_id] = CallbackAlarm(
                alarm_time=time.monotonic() + timeout,
                timer=timer,
            )

        timer.start()

    @overload
    def cancel_callback_timeout_alarm(
        self,
        sync_id: UUID,
    ) -> None: ...  # pragma: no cover

    @overload
    def cancel_callback_timeout_alarm(
        self,
        sync_id: UUID,
        return_remaining_time: Literal[True],
    ) -> float: ...  # pragma: no cover

    def cancel_callback_timeout_alarm(
        self,
        sync_id: UUID,
        return_remaining_time: bool = False,
    ) -> float | None:
        with self._lock:
            try:
                alarm = self._callback_alarms.pop(sync_id)
            except KeyError:
                raise BotXMethodCallbackNotFoundError(sync_id) from None

        alarm.timer.cancel()

        if return_remaining_time:
            return alarm.alarm_time - time.monotonic()

        return None

    def _setup_orphan_callback_alarm(self, sync_id: UUID, timeout: float) -> None:
        if sync_id in self._orphan_callback_alarms:
            return
        timer = threading.Timer(
            timeout,
            _orphan_callback_alarm,
            args=(self, sync_id, timeout),
        )
        timer.daemon = True
        self._orphan_callback_alarms[sync_id] = CallbackAlarm(
            alarm_time=time.monotonic() + timeout,
            timer=timer,
        )
        timer.start()

    def cancel_orphan_callback_alarm(self, sync_id: UUID) -> None:
        with self._lock:
            alarm = self._orphan_callback_alarms.pop(sync_id, None)
        if alarm is None:
            return
        alarm.timer.cancel()

    def mark_callback_expired(self, sync_id: UUID) -> None:
        self._mark_callback_expired(sync_id)

    def _mark_callback_expired(self, sync_id: UUID) -> None:
        with self._lock:
            self._expired_sync_ids.add(sync_id)
            self._pending_callbacks.pop(sync_id, None)
            self._expected_sync_ids.discard(sync_id)
        self.cancel_orphan_callback_alarm(sync_id)

    def drop_orphan_callback(self, sync_id: UUID) -> None:
        with self._lock:
            self._pending_callbacks.pop(sync_id, None)
        self.cancel_orphan_callback_alarm(sync_id)