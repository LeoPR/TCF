"""Estagio A: identificacao estendido pra granularidades finas.

Suporta:
- YYYY-MM-DD                              -> granularity=day
- YYYY-MM-DD[T ]HH:MM:SS                  -> granularity=second
- YYYY-MM-DD[T ]HH:MM:SS.fff               -> granularity=ms
- YYYY-MM-DD[T ]HH:MM:SS.ffffff            -> granularity=us
- YYYY-MM-DD[T ]HH:MM:SS.fffffffff         -> granularity=ns

Stage A so' inspeciona a primeira linha. Detector tenta o formato
mais especifico (ns) antes do menos especifico (day).
"""

from __future__ import annotations

import re
from datetime import date, datetime


_RE_YMD = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_YMD_HMS = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}$")
_RE_YMD_HMS_MS = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\.\d{3}$")
_RE_YMD_HMS_US = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\.\d{6}$")
_RE_YMD_HMS_NS = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\.\d{9}$")


def identify(linhas: list[str]) -> dict:
    meta: dict = {"n_samples": len(linhas)}
    if not linhas:
        meta["type"] = "unknown"
        meta["format"] = None
        meta["granularity"] = None
        return meta

    sample = linhas[0]

    # Ordem: mais especifico primeiro
    if _RE_YMD_HMS_NS.match(sample):
        sep = "T" if "T" in sample else " "
        meta["type"] = "date"
        meta["format"] = f"YYYY-MM-DD{sep}HH:MM:SS.fffffffff"
        meta["separator"] = sep
        meta["granularity"] = "ns"
        meta["frac_digits"] = 9
        return meta

    if _RE_YMD_HMS_US.match(sample):
        sep = "T" if "T" in sample else " "
        try:
            datetime.fromisoformat(sample.replace(" ", "T"))
            meta["type"] = "date"
            meta["format"] = f"YYYY-MM-DD{sep}HH:MM:SS.ffffff"
            meta["separator"] = sep
            meta["granularity"] = "us"
            meta["frac_digits"] = 6
            return meta
        except ValueError:
            pass

    if _RE_YMD_HMS_MS.match(sample):
        sep = "T" if "T" in sample else " "
        try:
            datetime.fromisoformat(sample.replace(" ", "T"))
            meta["type"] = "date"
            meta["format"] = f"YYYY-MM-DD{sep}HH:MM:SS.fff"
            meta["separator"] = sep
            meta["granularity"] = "ms"
            meta["frac_digits"] = 3
            return meta
        except ValueError:
            pass

    if _RE_YMD_HMS.match(sample):
        sep = "T" if "T" in sample else " "
        try:
            datetime.fromisoformat(sample.replace(" ", "T"))
            meta["type"] = "date"
            meta["format"] = f"YYYY-MM-DD{sep}HH:MM:SS"
            meta["separator"] = sep
            meta["granularity"] = "second"
            return meta
        except ValueError:
            pass

    if _RE_YMD.match(sample):
        try:
            date.fromisoformat(sample)
            meta["type"] = "date"
            meta["format"] = "YYYY-MM-DD"
            meta["granularity"] = "day"
            return meta
        except ValueError:
            pass

    meta["type"] = "string"
    meta["format"] = None
    meta["granularity"] = None
    return meta
