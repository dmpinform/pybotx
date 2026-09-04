from dataclasses import dataclass
from uuid import UUID

import urllib3

from pybotx.buffer import BufferWritable


@dataclass(slots=True)
class Sticker:
    """Sticker from sticker pack.

    Attributes:
        id: Sticker id.
        emoji: Sticker emoji.
        link: Sticker image link.
        pack_id: Sticker pack id.

    """

    id: UUID
    emoji: str
    image_link: str
    pack_id: UUID

    def download(
        self,
        buffer: BufferWritable,
        http_client: urllib3.PoolManager | None = None,
    ) -> None:
        client = http_client or urllib3.PoolManager()
        response = client.request("GET", self.image_link, preload_content=True)

        if not (200 <= response.status < 300):
            raise urllib3.exceptions.HTTPError(f"HTTP {response.status}")

        buffer.write(response.data)
        buffer.seek(0)


@dataclass(slots=True)
class StickerPack:
    """Sticker pack.

    Attributes:
        id: Sticker pack id.
        name: Sticker pack name.
        is_public: Is public pack.
        stickers: Stickers data.

    """

    id: UUID
    name: str
    is_public: bool
    stickers: list[Sticker]


@dataclass(slots=True)
class StickerPackFromList:
    """Sticker pack from list.

    Attributes:
        id: Sticker pack id.
        name: Sticker pack name.
        is_public: Is public pack
        stickers_count: Stickers count in pack
        sticker_ids: Stickers ids in pack

    """

    id: UUID
    name: str
    is_public: bool
    stickers_count: int
    sticker_ids: list[UUID] | None  # Can be omitted in result


@dataclass(slots=True)
class StickerPackPage:
    """Sticker pack page.

    Attributes:
        sticker_packs: Sticker pack list.
        after: Base64 string for pagination.

    """

    sticker_packs: list[StickerPackFromList]
    after: str | None
