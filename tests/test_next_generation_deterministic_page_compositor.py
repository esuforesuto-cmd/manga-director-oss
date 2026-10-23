from __future__ import annotations

import hashlib
import struct
import zlib
from fractions import Fraction

import pytest

from manga_director.production.next_generation_deterministic_page_compositor import (
    PNG_SIGNATURE,
    CompositeInputError,
    _axis_map,
    _blend,
    _cover_crops,
    _round_even,
    compose_page,
    decode_png,
    encode_rgb_png,
)
from manga_director.production.next_generation_page_composition import (
    AcceptedPanelSource,
    PageCompositionRequest,
)
from manga_director.production.next_generation_page_generation_plan import PanelRectangle


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _source_png(
    *,
    color_type: int = 2,
    bit_depth: int = 8,
    interlace: int = 0,
    samples: bytes = b"\x11\x22\x33",
    extra_chunks: tuple[tuple[bytes, bytes], ...] = (),
) -> bytes:
    header = struct.pack(">IIBBBBB", 1, 1, bit_depth, color_type, 0, 0, interlace)
    body = b"".join(_chunk(kind, payload) for kind, payload in extra_chunks)
    return (
        PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + body
        + _chunk(b"IDAT", zlib.compress(b"\x00" + samples))
        + _chunk(b"IEND", b"")
    )


def _coordinate(pixel: int, size: int) -> int:
    return (pixel * 1_000_000 + size - 1) // size


def _grid_rectangles(panel_count: int) -> tuple[PanelRectangle, ...]:
    side = {1: 1, 4: 2, 16: 4}[panel_count]
    panel_width = (1856 - (side - 1) * 48) // side
    panel_height = (2880 - (side - 1) * 48) // side
    rectangles: list[PanelRectangle] = []
    for row in range(side):
        for column in range(side):
            left = 96 + column * (panel_width + 48)
            top = 96 + row * (panel_height + 48)
            rectangles.append(
                PanelRectangle(
                    left=_coordinate(left, 2048),
                    top=_coordinate(top, 3072),
                    right=_coordinate(left + panel_width, 2048),
                    bottom=_coordinate(top + panel_height, 3072),
                )
            )
    return tuple(rectangles)


def _composition(panel_count: int) -> tuple[PageCompositionRequest, tuple[bytes, ...]]:
    rectangles = _grid_rectangles(panel_count)
    panel_pngs = tuple(
        encode_rgb_png(
            1,
            1,
            bytes(((index * 47) % 256, (index * 83) % 256, (index * 131) % 256)),
        )
        for index in range(1, panel_count + 1)
    )
    sources = tuple(
        AcceptedPanelSource(
            plan_id="plan-1",
            plan_fingerprint="a" * 64,
            project_id="project-1",
            page_id="page-1",
            panel_id=f"panel-{index}",
            panel_order=index,
            request_id=f"request-{index}",
            request_fingerprint=f"{(index + 1) % 10}" * 64,
            attempt_id=f"attempt-{index}",
            evidence_id=f"evidence-{index}",
            asset_id=f"asset-{index}",
            content_sha256=hashlib.sha256(panel_pngs[index - 1]).hexdigest(),
            width=1,
            height=1,
            rectangle=rectangles[index - 1],
        )
        for index in range(1, panel_count + 1)
    )
    return (
        PageCompositionRequest(
            composition_attempt_id=f"composition-{panel_count}",
            plan_id="plan-1",
            plan_fingerprint="a" * 64,
            project_id="project-1",
            page_id="page-1",
            explicit_authorization_reference="auth-1",
            composition_provenance_reference="provenance-1",
            panel_count=panel_count,
            sources=sources,
        ),
        panel_pngs,
    )


def _idat_payload(encoded: bytes) -> bytes:
    offset = len(PNG_SIGNATURE)
    payloads: list[bytes] = []
    while offset < len(encoded):
        length = struct.unpack_from(">I", encoded, offset)[0]
        kind = encoded[offset + 4 : offset + 8]
        payload = encoded[offset + 8 : offset + 8 + length]
        if kind == b"IDAT":
            payloads.append(payload)
        offset += length + 12
    return b"".join(payloads)


def test_canonical_encoder_emits_only_core_png_chunks_and_round_trips() -> None:
    pixels = bytes((255, 0, 0, 0, 255, 0))
    encoded = encode_rgb_png(2, 1, pixels)
    decoded = decode_png(encoded)
    assert (decoded.width, decoded.height, decoded.channels) == (2, 1, 3)
    assert decoded.pixels == pixels
    assert encoded.count(b"IHDR") == encoded.count(b"IDAT") == encoded.count(b"IEND") == 1


def test_stored_deflate_block_boundary_and_checksums_are_canonical() -> None:
    pixels = bytes((23, 41, 59)) * 21_845
    encoded = encode_rgb_png(21_845, 1, pixels)
    zstream = _idat_payload(encoded)
    assert zstream[:2] == b"\x78\x01"
    assert zstream[2] == 0
    length, complement = struct.unpack_from("<HH", zstream, 3)
    assert (length, complement) == (65_535, 0)
    second = 2 + 5 + 65_535
    assert zstream[second] == 1
    assert struct.unpack_from("<HH", zstream, second + 1) == (1, 65_534)
    raw = b"\x00" + pixels
    assert zstream[-4:] == struct.pack(">I", zlib.adler32(raw) & 0xFFFFFFFF)
    assert zlib.decompress(zstream) == raw
    offset = len(PNG_SIGNATURE)
    kinds: list[bytes] = []
    while offset < len(encoded):
        chunk_length = struct.unpack_from(">I", encoded, offset)[0]
        kind = encoded[offset + 4 : offset + 8]
        payload = encoded[offset + 8 : offset + 8 + chunk_length]
        crc = struct.unpack_from(">I", encoded, offset + 8 + chunk_length)[0]
        assert crc == zlib.crc32(kind + payload) & 0xFFFFFFFF
        kinds.append(kind)
        offset += chunk_length + 12
    assert kinds == [b"IHDR", b"IDAT", b"IEND"]


@pytest.mark.parametrize(
    ("panel_count", "expected_sha256"),
    [
        (1, "c1eaf7f0f23eb6edb28907d31763db901aa77ccb9273fd68e7e1d53903660f39"),
        (4, "789b8299a760015d4020832e921a72a2ae904e47699bd0881903770282b6f391"),
        (16, "49772fd44e42d940b041ebf051dcc1371467a6a4c7d936088fccdc66986c1d2d"),
    ],
)
def test_one_four_and_sixteen_panel_golden_sha256(
    panel_count: int, expected_sha256: str
) -> None:
    request, panel_pngs = _composition(panel_count)
    first = compose_page(request, panel_pngs)
    second = compose_page(request, panel_pngs)
    assert first == second
    assert hashlib.sha256(first).hexdigest() == expected_sha256


def test_four_panel_order_geometry_margins_and_gutters_are_exact() -> None:
    request, panel_pngs = _composition(4)
    composite = decode_png(compose_page(request, panel_pngs))
    assert composite.channels == 3
    assert composite.pixels[:3] == bytes((255, 255, 255))
    for source, panel_png in zip(request.sources, panel_pngs, strict=True):
        left, top, right, bottom = source.rectangle.to_pixels(
            request.canvas_width, request.canvas_height
        )
        center = (((top + bottom) // 2) * composite.width + (left + right) // 2) * 3
        assert composite.pixels[center : center + 3] == decode_png(panel_png).pixels[:3]
    first_right = request.sources[0].rectangle.to_pixels(2048, 3072)[2]
    second_left = request.sources[1].rectangle.to_pixels(2048, 3072)[0]
    gutter_x = (first_right + second_left) // 2
    gutter_y = sum(request.sources[0].rectangle.to_pixels(2048, 3072)[1::2]) // 2
    gutter = (gutter_y * composite.width + gutter_x) * 3
    assert composite.pixels[gutter : gutter + 3] == bytes((255, 255, 255))


def test_compositor_rejects_missing_mismatched_or_changed_sources() -> None:
    request, panel_pngs = _composition(1)
    with pytest.raises(CompositeInputError, match="source_count_mismatch"):
        compose_page(request, ())
    with pytest.raises(CompositeInputError, match="source_hash_mismatch"):
        compose_page(request, (panel_pngs[0] + b"x",))
    changed = encode_rgb_png(2, 1, bytes((1, 2, 3, 4, 5, 6)))
    rebound = request.model_copy(
        update={
            "sources": (
                request.sources[0].model_copy(
                    update={"content_sha256": hashlib.sha256(changed).hexdigest()}
                ),
            )
        }
    )
    with pytest.raises(CompositeInputError, match="source_dimension_mismatch"):
        compose_page(rebound, (changed,))
    four_panel_request, four_panel_pngs = _composition(4)
    with pytest.raises(CompositeInputError, match="source_hash_mismatch"):
        compose_page(four_panel_request, tuple(reversed(four_panel_pngs)))


def test_pixel_known_answers_cover_crop_fixed_point_and_round_even() -> None:
    assert _round_even(1, 2) == 0
    assert _round_even(3, 2) == 2
    assert _round_even(5, 2) == 2
    assert _cover_crops(4, 2, 2, 2) == (
        (Fraction(1), Fraction(2)),
        (Fraction(0), Fraction(2)),
    )
    assert _cover_crops(2, 4, 2, 2) == (
        (Fraction(0), Fraction(2)),
        (Fraction(1), Fraction(2)),
    )
    assert _cover_crops(2, 2, 2, 2) == (
        (Fraction(0), Fraction(2)),
        (Fraction(0), Fraction(2)),
    )
    assert _axis_map(2, 4, Fraction(0), Fraction(2)) == (
        (0, 1, 0),
        (0, 1, 16_384),
        (0, 1, 49_152),
        (1, 1, 0),
    )
    assert _axis_map(4, 2, Fraction(1), Fraction(2)) == (
        (1, 2, 0),
        (2, 2, 0),
    )
    assert _axis_map(4, 1, Fraction(11, 10), Fraction(1, 5)) == ((1, 1, 0),)
    assert _cover_crops(4, 2, 1, 1) == (
        (Fraction(1), Fraction(2)),
        (Fraction(0), Fraction(2)),
    )
    assert _cover_crops(2, 4, 1, 1) == (
        (Fraction(0), Fraction(2)),
        (Fraction(1), Fraction(2)),
    )
    assert _cover_crops(2, 2, 1, 1) == (
        (Fraction(0), Fraction(2)),
        (Fraction(0), Fraction(2)),
    )
    assert _blend(0, 1, 32_768) == 0
    assert _blend(1, 2, 32_768) == 2


def test_rgba_is_composited_onto_white_before_resampling() -> None:
    rgba = _source_png(color_type=6, samples=bytes((0, 0, 0, 128)))
    decoded = decode_png(rgba)
    assert decoded.channels == 4
    request, _ = _composition(1)
    rebound = request.model_copy(
        update={
            "sources": (
                request.sources[0].model_copy(
                    update={"content_sha256": hashlib.sha256(rgba).hexdigest()}
                ),
            )
        }
    )
    composite = decode_png(compose_page(rebound, (rgba,)))
    center = (1536 * composite.width + 1024) * 3
    assert composite.pixels[center : center + 3] == bytes((127, 127, 127))


@pytest.mark.parametrize(
    "invalid",
    [
        _source_png(color_type=0, samples=b"\x11"),
        _source_png(color_type=3, samples=b"\x00"),
        _source_png(bit_depth=16, samples=b"\x00" * 6),
        _source_png(interlace=1),
        _source_png(extra_chunks=((b"acTL", struct.pack(">II", 1, 0)),)),
        _source_png(extra_chunks=((b"PLTE", b"\x00\x00\x00"),)),
        _source_png() + b"trailing",
        _source_png()[:-1],
    ],
)
def test_decoder_rejects_unsupported_malformed_or_animated_png(invalid: bytes) -> None:
    with pytest.raises(CompositeInputError):
        decode_png(invalid)


def test_decoder_ignores_ancillary_metadata_without_copying_it() -> None:
    source = _source_png(
        extra_chunks=(
            (b"tRNS", b"\x00\x11\x00\x22\x00\x33"),
            (b"tEXt", b"Comment\x00untrusted"),
        )
    )
    decoded = decode_png(source)
    encoded = encode_rgb_png(decoded.width, decoded.height, decoded.pixels)
    assert decoded.channels == 3
    assert decoded.pixels == b"\x11\x22\x33"
    assert b"tRNS" not in encoded
    assert b"tEXt" not in encoded
    assert encoded.count(b"IHDR") == encoded.count(b"IDAT") == encoded.count(b"IEND") == 1


def test_decoder_and_encoder_reject_invalid_bounds() -> None:
    with pytest.raises(CompositeInputError):
        decode_png(b"not png")
    with pytest.raises(CompositeInputError):
        decode_png(b"\x89PNG\r\n\x1a\n\x00")
    with pytest.raises(CompositeInputError):
        encode_rgb_png(2, 1, b"\x00\x00\x00")


def test_decoder_rejects_source_byte_and_memory_budgets_before_decode() -> None:
    with pytest.raises(CompositeInputError, match="invalid_png"):
        decode_png(PNG_SIGNATURE + b"\x00" * (25 * 1024 * 1024))
    small_png = _source_png()
    with pytest.raises(CompositeInputError, match="decoded_memory_limit"):
        decode_png(small_png, memory_budget=1)


def test_compositor_preflights_all_source_hashes_before_canvas_work() -> None:
    request, panel_pngs = _composition(4)
    changed = (panel_pngs[0], panel_pngs[1], panel_pngs[2], panel_pngs[3] + b"changed")
    with pytest.raises(CompositeInputError, match="source_hash_mismatch"):
        compose_page(request, changed)
