"""Base resource class with common functionality."""

from uuid import UUID

from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.bot.exceptions import UnknownBotAccountError
from pybotx.bot.verification import verify_request
from pybotx.models.bot_account import BotAccountWithSecret


class BaseResource:
    """Base class for BotX resources with verification and credential management."""

    def __init__(
        self,
        bot_accounts_storage: BotAccountsStorage,
        verify_requests: bool = True,
    ) -> None:
        """Initialize base resource.

        :param bot_accounts_storage: BotAccountsStorage instance.
        :param verify_requests: Enable JWT verification.
        """
        self._bot_accounts_storage = bot_accounts_storage
        self._verify_requests = verify_requests

    def _verify_request(self, headers: dict[str, str]) -> BotAccountWithSecret:
        """Verify request and return bot account.

        :param headers: HTTP request headers.

        :return: BotAccountWithSecret that matches the token.
        :raises UnverifiedRequestError: If verification fails.
        """
        if not self._verify_requests:
            # For testing: return first credential without verification
            return list(self._bot_accounts_storage.iter_bot_accounts())[0]

        credentials = list(self._bot_accounts_storage.iter_bot_accounts())
        return verify_request(headers, credentials)

    def _get_bot_account(self, bot_id: UUID) -> BotAccountWithSecret:
        """Find bot account by ID.

        :param bot_id: Bot account ID.

        :return: BotAccountWithSecret with matching ID.
        :raises UnknownBotAccountError: If bot ID not found.
        """
        return self._bot_accounts_storage.get_bot_account(bot_id)
