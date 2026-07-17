"""Protótipo do escape D_json — extrai a IDEIA (não copia o core).

3 lacunas de D_json, 1 mecanismo: o alfabeto de escape `\\`+letra.

  VALOR (folha string):  `\\` -> `\\\\`   ·  LF -> `\\n`
  NOME (meta):           idem + nome VAZIO -> `\\z`   (slot livre; ver §invariante)

INVARIANTE que torna tudo injetivo (é a lógica do próprio JSON): o backslash é SEMPRE
dobrado primeiro. Logo, no fluxo escapado, um `\\` solto seguido de letra NUNCA vem de
dado — é sempre um marcador. `\\n` = LF; `\\z` = nome vazio; `\\\\n` = backslash+n literal.

Por que `\\z` p/ nome vazio (e não "emitir nada"): hoje "nome vazio no header" é o
SENTINELA DE CORRUPÇÃO da auditoria (parse:544). Emitir nada tornaria `{"":1}` legítimo
indistinguível de meta corrompido (`,a:2` / `a,,b`). Com `\\z` o sentinela FICA de pé.
"""
from __future__ import annotations

BS = chr(92)
LF = chr(10)

_SEP = ",[]{}:#?" + BS          # estruturais do meta (como no core)
_ESC_OK = _SEP + " "            # whitelist estrita do unescape (core)


# ------------------------------------------------------------------ VALOR (folha)
def esc_val(s: str) -> str:
    """Escapa só o que quebra o framing do L1 (LF) — e o próprio escape."""
    return s.replace(BS, BS + BS).replace(LF, BS + "n")


def unesc_val(s: str) -> str:
    """Unescape ESTRITO: só aceita o que esc_val emite; resto = corrupção (fail-loud)."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == BS:
            if i + 1 >= n:
                raise ValueError(f"escape dangling no valor {s!r}")
            nxt = s[i + 1]
            if nxt == "n":
                out.append(LF)
            elif nxt == BS:
                out.append(BS)
            else:
                raise ValueError(f"escape invalido '{BS}{nxt}' no valor {s!r}")
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


# ------------------------------------------------------------------ NOME (meta)
def esc_name(s: str) -> str:
    if s == "":
        return BS + "z"                       # nome VAZIO (slot livre; sentinela preservado)
    out = []
    for ch in s:
        if ch == LF:
            out.append(BS + "n")              # LF no nome (meta é 1 linha)
        elif ch in _SEP:
            out.append(BS + ch)
        else:
            out.append(ch)
    r = "".join(out)
    if r[0] == " ":                           # espaço INICIAL (o parser come " ," antes do nome)
        r = BS + r
    return r


def unesc_name(s: str) -> str:
    if s == BS + "z":
        return ""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == BS:
            if i + 1 >= n:
                raise ValueError(f"escape dangling no nome {s!r}")
            nxt = s[i + 1]
            if nxt == "n":
                out.append(LF)
            elif nxt in _ESC_OK:
                out.append(nxt)
            else:
                raise ValueError(f"escape de char nao-estrutural '{BS}{nxt}' no nome {s!r}")
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)
