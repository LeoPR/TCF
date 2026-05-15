"""Compressores com classificacao por natureza de uso.

Classes:
- `web/http`: HTTP/1.1+ e HTTP/3 Content-Encoding standard
- `file/archive`: compressao de arquivos / streaming arquivado
- `parquet`: padrao em Parquet (Apache columnar storage)
- `general`: standalone, sem caso de uso especifico

Compressor pode estar em multiplas classes. Vide
[`../notes/classificacao-compressores.md`](../notes/classificacao-compressores.md).
"""

from __future__ import annotations

import bz2
import gzip
import lzma

import brotli
import zstandard

_ZSTD_C = zstandard.ZstdCompressor(level=22)
_ZSTD_D = zstandard.ZstdDecompressor()


def _gz_c(b: bytes) -> bytes:
    return gzip.compress(b, compresslevel=9, mtime=0)


def _gz_d(b: bytes) -> bytes:
    return gzip.decompress(b)


def _br_c(b: bytes) -> bytes:
    return brotli.compress(b, quality=11)


def _br_d(b: bytes) -> bytes:
    return brotli.decompress(b)


def _zst_c(b: bytes) -> bytes:
    return _ZSTD_C.compress(b)


def _zst_d(b: bytes) -> bytes:
    return _ZSTD_D.decompress(b)


def _xz_c(b: bytes) -> bytes:
    return lzma.compress(b, preset=9)


def _xz_d(b: bytes) -> bytes:
    return lzma.decompress(b)


def _bz_c(b: bytes) -> bytes:
    return bz2.compress(b, compresslevel=9)


def _bz_d(b: bytes) -> bytes:
    return bz2.decompress(b)


COMPRESSORS: dict[str, dict] = {
    "gzip": {
        "compress":      _gz_c,
        "decompress":    _gz_d,
        "ext":           "gz",
        "level":         9,
        "lib":           "gzip (stdlib)",
        "classes":       ["web/http", "file/archive", "parquet", "general"],
        "http_encoding": "gzip",
        "rfc":           "RFC 1952",
    },
    "brotli": {
        "compress":      _br_c,
        "decompress":    _br_d,
        "ext":           "br",
        "level":         11,
        "lib":           "brotli 1.2.0",
        "classes":       ["web/http", "parquet"],
        "http_encoding": "br",
        "rfc":           "RFC 7932",
    },
    "zstd": {
        "compress":      _zst_c,
        "decompress":    _zst_d,
        "ext":           "zst",
        "level":         22,
        "lib":           "zstandard 0.25.0",
        "classes":       ["web/http", "file/archive", "parquet", "general"],
        "http_encoding": "zstd",
        "rfc":           "RFC 8478",
    },
    "lzma": {
        "compress":      _xz_c,
        "decompress":    _xz_d,
        "ext":           "xz",
        "level":         9,
        "lib":           "lzma (stdlib)",
        "classes":       ["file/archive"],
        "http_encoding": None,
        "rfc":           None,
    },
    "bz2": {
        "compress":      _bz_c,
        "decompress":    _bz_d,
        "ext":           "bz2",
        "level":         9,
        "lib":           "bz2 (stdlib)",
        "classes":       ["file/archive"],
        "http_encoding": None,
        "rfc":           None,
    },
}


def class_members() -> dict[str, list[str]]:
    """`{classe: [compressors_pertencentes]}`."""
    out: dict[str, list[str]] = {}
    for name, meta in COMPRESSORS.items():
        for cls in meta["classes"]:
            out.setdefault(cls, []).append(name)
    return out


CLASSES = ["web/http", "file/archive", "parquet", "general"]
