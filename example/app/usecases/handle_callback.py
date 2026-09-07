"""UseCase для обработки callback от BotX API."""

from pybotx import BotAPIMethodFailedCallback, BotAPIMethodSuccessfulCallback
from pybotx.logger import logger


class HandleCallback:
    """UseCase для обработки входящих callback от BotX."""

    def execute(self, callback: BotAPIMethodSuccessfulCallback | BotAPIMethodFailedCallback) -> None:
        """Обработать callback.

        :param callback: Callback от BotX API.
        """
        sync_id = callback.sync_id

        if isinstance(callback, BotAPIMethodSuccessfulCallback):
            # Успешный callback
            logger.info(
                f"✓ Callback успешно получен: sync_id={sync_id}, result={callback.result}"
            )
            # Здесь можно:
            # - сохранить результат в БД
            # - обновить статус операции
            # - отправить уведомление
            # - обновить метрики
        else:
            # Ошибка в callback
            logger.error(
                f"✗ Callback с ошибкой: sync_id={sync_id}, "
                f"reason={callback.reason}, errors={callback.errors}"
            )
            # Здесь можно:
            # - залогировать ошибку
            # - отправить алерт
            # - повторить операцию
            # - откатить изменения
