from collections.abc import Sequence
from typing import TypeVar

TItem = TypeVar("TItem")


def optional_sequence_to_list(
    optional_sequence: Sequence[TItem] | None,
) -> list[TItem]:
    return list(optional_sequence or [])
