from __future__ import annotations

from PIL import Image

from .crypto import decrypt_payload, encrypt_payload
from .noise import embedding_order, load_noise_rgba, noise_fingerprint


def _prepare_cover(path: str) -> Image.Image:
    img = Image.open(path)
    if img.size[0] != img.size[1]:
        pass
    return img.convert("RGBA")


def _bits_from_bytes(data: bytes) -> list[int]:
    bits: list[int] = []
    for byte in data:
        for i in range(8):
            bits.append((byte >> (7 - i)) & 1)
    return bits


def _bytes_from_bits(bits: list[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits), 8):
        chunk = bits[i : i + 8]
        if len(chunk) < 8:
            break
        value = 0
        for b in chunk:
            value = (value << 1) | b
        out.append(value)
    return bytes(out)


def _capacity_bits(width: int, height: int) -> int:
    return width * height * 3


def embed_message(
    cover_path: str,
    noise_path: str,
    message: str,
    output_path: str,
    password: str | None = None,
) -> dict:
    noise = load_noise_rgba(noise_path)
    cover = _prepare_cover(cover_path)

    if cover.size != noise.size:
        raise ValueError(
            f"Размеры не совпадают: картинка {cover.size}, карта шума {noise.size}."
        )

    fp = noise_fingerprint(noise)
    payload = message.encode("utf-8")
    packet = encrypt_payload(payload, fp, password)
    bits = _bits_from_bytes(packet)

    cap = _capacity_bits(*cover.size)
    if len(bits) > cap:
        raise ValueError(
            f"Сообщение слишком длинное: нужно {len(bits)} бит, доступно {cap}."
        )

    order = embedding_order(noise)
    px = cover.load()
    channels = (0, 1, 2)
    bit_idx = 0
    pos_idx = 0
    ch_idx = 0

    while bit_idx < len(bits):
        x, y = order[pos_idx % len(order)]
        pos_idx += 1
        pixel = list(px[x, y])
        ch = channels[ch_idx % 3]
        ch_idx += 1
        pixel[ch] = (pixel[ch] & 0xFE) | bits[bit_idx]
        px[x, y] = tuple(pixel)
        bit_idx += 1

    cover.save(output_path, format="PNG")
    return {
        "bytes_embedded": len(packet),
        "bits_used": len(bits),
        "capacity_bits": cap,
    }


def extract_message(
    stego_path: str,
    noise_path: str,
    password: str | None = None,
) -> str:
    noise = load_noise_rgba(noise_path)
    stego = _prepare_cover(stego_path)

    if stego.size != noise.size:
        raise ValueError(
            f"Размеры не совпадают: картинка {stego.size}, карта шума {noise.size}."
        )

    fp = noise_fingerprint(noise)
    order = embedding_order(noise)
    px = stego.load()
    channels = (0, 1, 2)

    cap = _capacity_bits(*stego.size)
    bits: list[int] = []
    pos_idx = 0
    ch_idx = 0

    while len(bits) < cap:
        x, y = order[pos_idx % len(order)]
        pos_idx += 1
        pixel = px[x, y]
        ch = channels[ch_idx % 3]
        ch_idx += 1
        bits.append(pixel[ch] & 1)

        if len(bits) >= 80:
            header = _bytes_from_bits(bits[:80])
            if header[:4] == b"PNGC":
                length = int.from_bytes(header[6:10], "big")
                total_bits = (10 + length) * 8
                if len(bits) >= total_bits:
                    packet = _bytes_from_bits(bits[:total_bits])
                    plain = decrypt_payload(packet, fp, password)
                    return plain.decode("utf-8")

    raise ValueError("Скрытое сообщение не найдено. Проверьте карту шума, пароль и файл.")
