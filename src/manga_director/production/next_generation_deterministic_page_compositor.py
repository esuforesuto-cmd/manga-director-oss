"""Pure deterministic RGB PNG compositor for ``md-page-compositor-v1``."""

from __future__ import annotations

import hashlib
import struct
import zlib
from dataclasses import dataclass
from fractions import Fraction

from manga_director.production.next_generation_page_composition import PageCompositionRequest

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_MAX_SOURCE_BYTES = 25 * 1024 * 1024
_MAX_SOURCE_PIXELS = 32_000_000
_MAX_DECODED_BYTES = 128 * 1024 * 1024
_MAX_OUTPUT_BYTES = 25 * 1024 * 1024


class CompositeInputError(ValueError):
    """Raised when an input is unsupported or violates a frozen bound."""


@dataclass(frozen=True, slots=True)
class DecodedPNG:
    width: int
    height: int
    channels: int
    pixels: bytes | memoryview


def compose_page(request: PageCompositionRequest, panel_pngs: tuple[bytes, ...]) -> bytes:
    """Compose canonical source PNG bytes according to the immutable request."""

    if len(panel_pngs) != len(request.sources):
        raise CompositeInputError("source_count_mismatch")
    canvas_size = request.canvas_width * request.canvas_height * 3
    if canvas_size + _MAX_SOURCE_BYTES * 2 > _MAX_DECODED_BYTES:
        raise CompositeInputError("decoded_memory_limit")
    for source, data in zip(request.sources, panel_pngs, strict=True):
        if not isinstance(data, bytes) or len(data) > _MAX_SOURCE_BYTES:
            raise CompositeInputError("source_byte_limit")
        if hashlib.sha256(data).hexdigest() != source.content_sha256:
            raise CompositeInputError("source_hash_mismatch")
    canvas = bytearray(b"\xff") * canvas_size
    total_pixels = 0
    for source, data in zip(request.sources, panel_pngs, strict=True):
        image = decode_png(data, memory_budget=_MAX_DECODED_BYTES - len(canvas))
        if (image.width, image.height) != (source.width, source.height):
            raise CompositeInputError("source_dimension_mismatch")
        total_pixels += image.width * image.height
        if total_pixels > _MAX_SOURCE_PIXELS:
            raise CompositeInputError("aggregate_pixel_limit")
        if len(image.pixels) + len(canvas) > _MAX_DECODED_BYTES:
            raise CompositeInputError("decoded_memory_limit")
        _draw_cover_center(
            canvas,
            request.canvas_width,
            image,
            source.rectangle.to_pixels(request.canvas_width, request.canvas_height),
        )
        del image
    output = encode_rgb_png(request.canvas_width, request.canvas_height, bytes(canvas))
    if len(output) > _MAX_OUTPUT_BYTES:
        raise CompositeInputError("composite_byte_limit")
    return output


def decode_png(
    data: bytes, *, memory_budget: int = _MAX_DECODED_BYTES
) -> DecodedPNG:
    """Decode strict, static RGB/RGBA8 non-interlaced PNG into raw pixels."""

    if (
        not isinstance(data, bytes)
        or len(data) > _MAX_SOURCE_BYTES
        or len(data) < 45
        or not data.startswith(PNG_SIGNATURE)
    ):
        raise CompositeInputError("invalid_png")
    offset = len(PNG_SIGNATURE)
    header: bytes | None = None
    idat_parts: list[bytes] = []
    saw_idat = False
    idat_ended = False
    ended = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise CompositeInputError("truncated_png_chunk")
        length = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise CompositeInputError("truncated_png_chunk")
        payload = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack_from(">I", data, offset + 8 + length)[0]
        if len(kind) != 4 or any(not (65 <= byte <= 90 or 97 <= byte <= 122) for byte in kind):
            raise CompositeInputError("invalid_png_chunk_type")
        if kind[2] & 0x20:
            raise CompositeInputError("invalid_png_chunk_type")
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected_crc:
            raise CompositeInputError("png_crc_mismatch")
        if header is None and kind != b"IHDR":
            raise CompositeInputError("invalid_png_structure")
        if kind == b"IHDR":
            if header is not None or offset != len(PNG_SIGNATURE):
                raise CompositeInputError("invalid_png_structure")
            header = payload
        elif kind == b"IDAT":
            if idat_ended:
                raise CompositeInputError("nonconsecutive_idat")
            saw_idat = True
            idat_parts.append(payload)
        if kind == b"IEND":
            if length or end != len(data) or not saw_idat:
                raise CompositeInputError("trailing_png_data")
            ended = True
            break
        if kind in {b"acTL", b"fcTL", b"fdAT"}:
            raise CompositeInputError("animated_png_not_supported")
        if kind not in {b"IHDR", b"IDAT", b"IEND"}:
            if kind[0] & 0x20 == 0:
                raise CompositeInputError("unsupported_png_chunk")
            if saw_idat:
                idat_ended = True
        offset = end
    if not ended or header is None or not saw_idat:
        raise CompositeInputError("invalid_png_structure")
    if len(header) != 13:
        raise CompositeInputError("invalid_ihdr")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", header
    )
    if not width or not height or width > 4096 or height > 4096:
        raise CompositeInputError("png_dimensions_out_of_bounds")
    if depth != 8 or color not in (2, 6) or compression or filtering or interlace:
        raise CompositeInputError("unsupported_png_format")
    compressed_size = sum(map(len, idat_parts))
    if not compressed_size:
        raise CompositeInputError("invalid_png_deflate_stream")
    channels = 3 if color == 2 else 4
    stride = width * channels
    expected_length = height * (stride + 1)
    if expected_length + compressed_size * 2 > memory_budget:
        raise CompositeInputError("decoded_memory_limit")
    return DecodedPNG(
        width,
        height,
        channels,
        _decode_scanlines(idat_parts, width, height, channels),
    )


def encode_rgb_png(width: int, height: int, pixels: bytes) -> bytes:
    """Encode canonical RGB8 PNG with stored DEFLATE blocks and no metadata."""

    if width < 1 or height < 1 or len(pixels) != width * height * 3:
        raise CompositeInputError("invalid_rgb_pixels")
    raw_length = height * (width * 3 + 1)
    zstream = bytearray(b"\x78\x01")
    block = bytearray()
    raw_emitted = 0
    adler = 1
    view = memoryview(pixels)
    for row in range(height):
        row_start = row * width * 3
        parts = (memoryview(b"\x00"), view[row_start : row_start + width * 3])
        for part in parts:
            adler = zlib.adler32(part, adler)
            part_offset = 0
            while part_offset < len(part):
                take = min(65535 - len(block), len(part) - part_offset)
                block.extend(part[part_offset : part_offset + take])
                part_offset += take
                if len(block) == 65535:
                    final = raw_emitted + len(block) == raw_length
                    _append_stored_block(zstream, block, final)
                    raw_emitted += len(block)
                    block.clear()
    if block:
        _append_stored_block(zstream, block, True)
        raw_emitted += len(block)
    if raw_emitted != raw_length:
        raise CompositeInputError("invalid_rgb_pixels")
    zstream.extend(struct.pack(">I", adler & 0xFFFFFFFF))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    output = (
        PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", bytes(zstream))
        + _chunk(b"IEND", b"")
    )
    if len(output) > _MAX_OUTPUT_BYTES:
        raise CompositeInputError("composite_byte_limit")
    return output


def _draw_cover_center(
    canvas: bytearray,
    canvas_width: int,
    image: DecodedPNG,
    rectangle: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = rectangle
    target_width = right - left
    target_height = bottom - top
    x_crop, y_crop = _cover_crops(
        image.width, image.height, target_width, target_height
    )
    x_map = _axis_map(image.width, target_width, *x_crop)
    y_map = _axis_map(image.height, target_height, *y_crop)

    if image.width == image.height == 1:
        color = bytes(_source_rgb(image, 0, 0))
        row_pixels = color * target_width
        for destination_y in range(top, bottom):
            target = (destination_y * canvas_width + left) * 3
            canvas[target : target + len(row_pixels)] = row_pixels
        return

    for destination_y, (lower_y, upper_y, weight_y) in enumerate(y_map, start=top):
        for destination_x, (lower_x, upper_x, weight_x) in enumerate(x_map, start=left):
            upper_left = _source_rgb(image, lower_x, lower_y)
            upper_right = _source_rgb(image, upper_x, lower_y)
            lower_left = _source_rgb(image, lower_x, upper_y)
            lower_right = _source_rgb(image, upper_x, upper_y)
            rgb = tuple(
                _blend(
                    _blend(upper_left[channel], upper_right[channel], weight_x),
                    _blend(lower_left[channel], lower_right[channel], weight_x),
                    weight_y,
                )
                for channel in range(3)
            )
            target = (destination_y * canvas_width + destination_x) * 3
            canvas[target : target + 3] = bytes(rgb)


def _decode_scanlines(
    compressed_parts: list[bytes], width: int, height: int, channels: int
) -> bytes:
    stride = width * channels
    row_length = stride + 1
    pixels = bytearray(height * stride)
    pending = bytearray()
    inflater = zlib.decompressobj()
    part_index = 0
    part_offset = 0
    row = 0

    try:
        while row < height:
            if inflater.unconsumed_tail:
                feed = inflater.unconsumed_tail
            elif part_index < len(compressed_parts):
                part = compressed_parts[part_index]
                feed = part[part_offset : part_offset + 65_536]
                part_offset += len(feed)
                if part_offset == len(part):
                    part_index += 1
                    part_offset = 0
            else:
                feed = b""
            output = inflater.decompress(feed, row_length - len(pending))
            pending.extend(output)
            if len(pending) == row_length:
                _reconstruct_scanline(
                    pending[0],
                    pending[1:],
                    pixels,
                    row,
                    stride,
                    channels,
                )
                pending.clear()
                row += 1
                continue
            if (
                not output
                and not inflater.unconsumed_tail
                and part_index >= len(compressed_parts)
            ):
                raise CompositeInputError("invalid_png_deflate_stream")

        while not inflater.eof:
            if inflater.unconsumed_tail:
                feed = inflater.unconsumed_tail
            elif part_index < len(compressed_parts):
                part = compressed_parts[part_index]
                feed = part[part_offset : part_offset + 65_536]
                part_offset += len(feed)
                if part_offset == len(part):
                    part_index += 1
                    part_offset = 0
            else:
                feed = b""
            output = inflater.decompress(feed, 1)
            if output:
                raise CompositeInputError("invalid_png_deflate_stream")
            if (
                not inflater.eof
                and not inflater.unconsumed_tail
                and part_index >= len(compressed_parts)
            ):
                raise CompositeInputError("invalid_png_deflate_stream")
    except zlib.error as error:
        raise CompositeInputError("invalid_png_deflate_stream") from error

    if (
        pending
        or inflater.unused_data
        or inflater.unconsumed_tail
        or part_index != len(compressed_parts)
    ):
        raise CompositeInputError("invalid_png_deflate_stream")
    return memoryview(pixels).toreadonly()


def _reconstruct_scanline(
    filter_type: int,
    scanline: bytes | bytearray,
    pixels: bytearray,
    row: int,
    stride: int,
    channels: int,
) -> None:
    if filter_type not in range(5):
        raise CompositeInputError("unsupported_png_filter")
    row_start = row * stride
    prior_start = row_start - stride
    for index, byte in enumerate(scanline):
        left = pixels[row_start + index - channels] if index >= channels else 0
        up = pixels[prior_start + index] if row else 0
        upper_left = (
            pixels[prior_start + index - channels]
            if row and index >= channels
            else 0
        )
        if filter_type == 0:
            predictor = 0
        elif filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = up
        elif filter_type == 3:
            predictor = (left + up) // 2
        else:
            predictor = _paeth(left, up, upper_left)
        pixels[row_start + index] = (byte + predictor) & 0xFF


def _cover_crops(
    source_width: int, source_height: int, target_width: int, target_height: int
) -> tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction]]:
    source_ratio_cross = source_width * target_height
    target_ratio_cross = source_height * target_width
    if source_ratio_cross > target_ratio_cross:
        x_extent = Fraction(source_height * target_width, target_height)
        x_start = (Fraction(source_width) - x_extent) / 2
        return (x_start, x_extent), (Fraction(0), Fraction(source_height))
    if source_ratio_cross < target_ratio_cross:
        y_extent = Fraction(source_width * target_height, target_width)
        y_start = (Fraction(source_height) - y_extent) / 2
        return (Fraction(0), Fraction(source_width)), (y_start, y_extent)
    return (
        (Fraction(0), Fraction(source_width)),
        (Fraction(0), Fraction(source_height)),
    )


def _axis_map(
    source_size: int,
    destination_size: int,
    crop_start: Fraction,
    crop_extent: Fraction,
) -> tuple[tuple[int, int, int], ...]:
    tap_min = max(0, _ceil_fraction(crop_start - Fraction(1, 2)))
    tap_max = min(
        source_size - 1, _floor_fraction(crop_start + crop_extent - Fraction(1, 2))
    )
    if tap_min > tap_max:
        midpoint = crop_start + crop_extent / 2 - Fraction(1, 2)
        lower = _floor_fraction(midpoint)
        remainder = midpoint - lower
        nearest = lower if remainder <= Fraction(1, 2) else lower + 1
        nearest = min(source_size - 1, max(0, nearest))
        return tuple((nearest, nearest, 0) for _ in range(destination_size))

    result: list[tuple[int, int, int]] = []
    for index in range(destination_size):
        source = (
            crop_start
            + Fraction((2 * index + 1), 2 * destination_size) * crop_extent
            - Fraction(1, 2)
        )
        source = min(Fraction(tap_max), max(Fraction(tap_min), source))
        lower = _floor_fraction(source)
        upper = min(lower + 1, tap_max)
        weight = _floor_fraction((source - lower) * 65_536)
        result.append((lower, upper, weight))
    return tuple(result)


def _source_rgb(image: DecodedPNG, x: int, y: int) -> tuple[int, int, int]:
    offset = (y * image.width + x) * image.channels
    red, green, blue = image.pixels[offset : offset + 3]
    if image.channels == 3:
        return red, green, blue
    alpha = image.pixels[offset + 3]
    return (
        _round_even(red * alpha + 255 * (255 - alpha), 255),
        _round_even(green * alpha + 255 * (255 - alpha), 255),
        _round_even(blue * alpha + 255 * (255 - alpha), 255),
    )


def _blend(lower: int, upper: int, weight: int) -> int:
    if weight == 0 or lower == upper:
        return lower
    return _round_even(lower * (65_536 - weight) + upper * weight, 65_536)


def _floor_fraction(value: Fraction) -> int:
    return value.numerator // value.denominator


def _ceil_fraction(value: Fraction) -> int:
    return -(-value.numerator // value.denominator)


def _append_stored_block(stream: bytearray, block: bytearray, final: bool) -> None:
    if not 1 <= len(block) <= 65_535:
        raise CompositeInputError("invalid_stored_block")
    stream.append(1 if final else 0)
    stream.extend(struct.pack("<HH", len(block), len(block) ^ 0xFFFF))
    stream.extend(block)


def _round_even(numerator: int, denominator: int) -> int:
    quotient, remainder = divmod(numerator, denominator)
    twice = remainder * 2
    return quotient + int(twice > denominator or (twice == denominator and quotient % 2 == 1))


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    distances = (abs(estimate - left), abs(estimate - up), abs(estimate - upper_left))
    if distances[0] <= distances[1] and distances[0] <= distances[2]:
        return left
    return up if distances[1] <= distances[2] else upper_left


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )
