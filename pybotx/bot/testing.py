from collections.abc import Iterator
from contextlib import contextmanager

from pybotx.bot.bot import Bot


@contextmanager
def lifespan_wrapper(bot: Bot) -> Iterator[Bot]:
    bot.startup()

    try:
        yield bot
    finally:
        bot.shutdown()