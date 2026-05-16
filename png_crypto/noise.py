from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "orders"


def load_noise_rgba(path: str) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    return img


def noise_fingerprint(noise: Image.Image) -> bytes:
    return hashlib.sha256(noise.tobytes()).digest()


def _order_cache_path(fp: bytes) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{fp.hex()}.npy"


def embedding_order(noise: Image.Image) -> list[tuple[int, int]]:
    """Deterministic pixel visit order derived from the noise map."""
    fp = noise_fingerprint(noise)
    cache = _order_cache_path(fp)
    if cache.is_file():
        arr = np.load(cache)
        return [(int(x), int(y)) for x, y in arr]

    w, h = noise.size
    arr = np.array(noise, dtype=np.uint32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    ys, xs = np.mgrid[0:h, 0:w]
    scores = (
        (r.astype(np.uint64) << 24)
        ^ (g.astype(np.uint64) << 16)
        ^ (b.astype(np.uint64) << 8)
        ^ a.astype(np.uint64)
        ^ (xs.astype(np.uint64) * 92837111)
        ^ (ys.astype(np.uint64) * 689287499)
    )
    flat = scores.ravel()
    order_idx = np.argsort(flat, kind="stable")
    xs_flat = xs.ravel()
    ys_flat = ys.ravel()
    positions = np.column_stack((xs_flat[order_idx], ys_flat[order_idx]))
    np.save(cache, positions.astype(np.int32))
    return [(int(x), int(y)) for x, y in positions]
