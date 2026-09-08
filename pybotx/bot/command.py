"""Базовый класс для обработчиков команд бота."""

from typing import Any

from pybotx.models.commands import BotCommand


class Command:
    """Базовый обработчик команд."""

    def __init__(self, usecase: Any) -> None:
        """Initialize handler with UseCase.

        :param usecase: UseCase instance to execute.
        """
        self._usecase = usecase

    def execute(self, message: BotCommand) -> None:
        """Execute command by running UseCase.

        :param message: Incoming message or system event from BotX.
        """
        self._usecase.execute(message)
