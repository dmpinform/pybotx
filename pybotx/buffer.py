import os
from typing import Protocol


class BufferBase(Protocol):
    def seek(
        self,
        offset: int,
        whence: int = os.SEEK_SET,
    ) -> int: ...  # pragma: no cover

    def tell(self) -> int: ...  # pragma: no cover


class BufferWritable(BufferBase, Protocol):
    def write(self, content: bytes) -> int: ...  # pragma: no cover


class BufferReadable(BufferBase, Protocol):
    def read(self, size: int = -1, /) -> bytes: ...  # pragma: no cover


def get_file_size(buffer: BufferReadable) -> int:
    buffer.seek(0, os.SEEK_END)
    file_size = buffer.tell()
    buffer.seek(0)
    return file_size
