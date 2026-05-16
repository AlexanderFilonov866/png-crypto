from __future__ import annotations

import hashlib
import os
import zlib

MAGIC = b"PNGC"
VERSION = 1


def keystream(seed: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def _pack_plain(plain: bytes) -> bytes:
    return plain + zlib.crc32(plain).to_bytes(4, "big")


def _unpack_plain(data: bytes) -> bytes:
    if len(data) < 4:
        raise ValueError("Повреждённые данные.")
    payload, crc = data[:-4], int.from_bytes(data[-4:], "big")
    if zlib.crc32(payload) & 0xFFFFFFFF != crc:
        raise ValueError("Контрольная сумма не совпала — неверный пароль или карта шума.")
    return payload


def encrypt_payload(plain: bytes, noise_fp: bytes, password: str | None) -> bytes:
    packed = _pack_plain(plain)
    seed = noise_fp
    if password:
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt + noise_fp,
            120_000,
            dklen=32,
        )
        seed = key
        stream = keystream(seed, len(packed))
        body_cipher = bytes(b ^ s for b, s in zip(packed, stream))
        cipher = salt + body_cipher
    else:
        stream = keystream(seed, len(packed))
        cipher = bytes(b ^ s for b, s in zip(packed, stream))
    header = MAGIC + bytes([VERSION, 1 if password else 0]) + len(cipher).to_bytes(4, "big")
    return header + cipher


def decrypt_payload(packet: bytes, noise_fp: bytes, password: str | None) -> bytes:
    if len(packet) < 10 or packet[:4] != MAGIC:
        raise ValueError("Сообщение не найдено или повреждено (неверная сигнатура).")
    version = packet[4]
    if version != VERSION:
        raise ValueError(f"Неподдерживаемая версия формата: {version}.")
    has_password = packet[5] == 1
    length = int.from_bytes(packet[6:10], "big")
    cipher = packet[10 : 10 + length]
    if len(cipher) != length:
        raise ValueError("Обрезанные данные в изображении.")

    if has_password:
        if not password:
            raise ValueError("Для расшифровки нужен пароль.")
        if len(cipher) < 16:
            raise ValueError("Повреждённые данные.")
        salt, body_cipher = cipher[:16], cipher[16:]
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt + noise_fp,
            120_000,
            dklen=32,
        )
        seed = key
    else:
        if password:
            raise ValueError("Сообщение зашифровано без пароля — оставьте поле пароля пустым.")
        seed = noise_fp
        body_cipher = cipher

    stream = keystream(seed, len(body_cipher))
    body = bytes(b ^ s for b, s in zip(body_cipher, stream))
    return _unpack_plain(body)
