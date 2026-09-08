"""Базовый класс для обработчиков колбэков бота."""

from typing import Any

from pybotx.models.method_callbacks import BotXMethodCallback


class Callback:
    """Базовый обработчик колбэков."""

    def __init__(self, usecase: Any) -> None:
        """Initialize handler with UseCase.

        :param usecase: UseCase instance to execute.
        """
        self._usecase = usecase

    def execute(self, message: BotXMethodCallback) -> None:
        """Execute command by running UseCase.

        :param message: Incoming message from BotX.
        :param client: Client instance for sending responses.
        """
        # Выполнить usecase
        self._usecase.execute(message)
