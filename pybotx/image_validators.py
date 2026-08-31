from pybotx.buffer import BufferReadable, get_file_size
from pybotx.constants import STICKER_IMAGE_MAX_SIZE

PNG_MAGIC_BYTES: bytes = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"


def ensure_file_content_is_png(buffer: BufferReadable) -> None:
    magic_bytes = buffer.read(8)

    buffer.seek(0)

    if magic_bytes != PNG_MAGIC_BYTES:
        raise ValueError("Passed file is not PNG")


def ensure_sticker_image_size_valid(buffer: BufferReadable) -> None:
    file_size = get_file_size(buffer)

    if file_size > STICKER_IMAGE_MAX_SIZE:
        max_file_size_mb = STICKER_IMAGE_MAX_SIZE / 1024 / 1024
        raise ValueError(
            f"Passed file size is greater than {max_file_size_mb:.1f} Mb",
        )
