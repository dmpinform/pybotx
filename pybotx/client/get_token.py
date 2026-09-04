from uuid import UUID

import urllib3

from pybotx.bot.bot_accounts_storage import BotAccountsStorage
from pybotx.client.bots_api.get_token import (
    BotXAPIGetTokenRequestPayload,
    GetTokenMethod,
)


def get_token(
    bot_id: UUID,
    http_client: urllib3.PoolManager,
    bot_accounts_storage: BotAccountsStorage,
) -> str:
    """Request token for bot.

    Moved to separate file because used in `AuthorizedBotXMethod` and `Bot.get_token`.
    """

    method = GetTokenMethod(
        bot_id,
        http_client,
        bot_accounts_storage,
    )

    signature = bot_accounts_storage.build_signature(bot_id)
    payload = BotXAPIGetTokenRequestPayload.from_domain(signature)

    botx_api_token = method.execute(payload)

    return botx_api_token.to_domain()
