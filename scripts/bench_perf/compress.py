"""Compressores externos, com NIVEL CANONICO fixo — conserta a incoerencia de
labs (gzip 6 vs 9, brotli q11 vs q5, zstd 19 vs 22 vs 3).

A regra que fecha a lacuna do eixo compressao: o MESMO compressor, no MESMO
nivel, aplicado a TODOS os caminhos (tcf, csv, json crus). Assim "gzip direto no
CSV" ganha cronometro, e o trade-off tempo x bytes vira comparavel.

Nivel ausente no ambiente -> a celula e' pulada com motivo (o manifesto ja'
registra quem existe), nunca fallback calado.
"""

from __future__ import annotations

import gzip
import zlib


def _gzip(level):
    return (lambda b: zlib.compress(b, level), zlib.decompress)


def _brotli(quality):
    import brotli
    return (lambda b: brotli.compress(b, quality=quality), brotli.decompress)


def _zstd(level):
    import zstandard as zstd
    c = zstd.ZstdCompressor(level=level)
    d = zstd.ZstdDecompressor()
    return (lambda b: c.compress(b), lambda b: d.decompress(b))


# nome canonico -> fabrica (compress, decompress). Niveis FIXOS.
CODECS = {
    "gzip-6": lambda: _gzip(6),
    "gzip-9": lambda: _gzip(9),
    "zstd-3": lambda: _zstd(3),
    "zstd-19": lambda: _zstd(19),
    "brotli-5": lambda: _brotli(5),
    "brotli-11": lambda: _brotli(11),
}


def get(nome):
    """(compress, decompress) ou levanta se o compressor nao esta' no ambiente."""
    if nome not in CODECS:
        raise KeyError(f"codec desconhecido: {nome}")
    return CODECS[nome]()      # pode levantar ImportError se a lib faltar


__all__ = ["CODECS", "get"]
