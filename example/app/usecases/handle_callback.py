"""UseCase для обработки callback от BotX API."""

import logging

from pybotx import BotAPIMethodSuccessfulCallback


class HandleCallback:
    """UseCase для обработки входящих callback от BotX."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def execute(self, callback) -> None:
        """Обработать callback.

        :param callback: Callback от BotX API.
        """
        sync_id = callback.sync_id

        if isinstance(callback, BotAPIMethodSuccessfulCallback):
            # Успешный callback
            self.logger.info(
                f"✓ Callback успешно получен: sync_id={sync_id}, result={callback.result}"
            )
            # Здесь можно:
            # - сохранить результат в БД
            # - обновить статус операции
            # - отправить уведомление
            # - обновить метрики
        else:
            # Ошибка в callback
            self.logger.error(
                f"✗ Callback с ошибкой: sync_id={sync_id}, "
                f"reason={callback.reason}, errors={callback.errors}"
            )
            # Здесь можно:
            # - залогировать ошибку
            # - отправить алерт
            # - повторить операцию
            # - откатить изменения
