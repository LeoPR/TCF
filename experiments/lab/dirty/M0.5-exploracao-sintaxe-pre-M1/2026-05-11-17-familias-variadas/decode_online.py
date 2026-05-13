"""Decoder do formato online.

Cada linha:
  noN: forma                 declaracao (count implicito = 1)
  noN: Mx forma              declaracao com RLE adjacente
  ref:noN                    referencia (count implicito = 1)
  Mx ref:noN                 referencia com RLE adjacente

`forma` = tokens separados por ' + '. Tokens:
  '"X"'             literal
  'noN[0:K]'        primeiros K chars de noN
  'noN[-K:]'        ultimos K chars de noN

Decode em 1 passada — strings sao construidas em ordem, refs a
anteriores ja estao disponiveis.
"""

import re

RE_REF_PREF = re.compile(r'^no(\d+)\[0:(\d+)\]$')
RE_REF_SUF = re.compile(r'^no(\d+)\[-(\d+):\]$')
RE_LIT = re.compile(r'^"(.*)"$')
RE_DECL = re.compile(r'^no(\d+): (?:(\d+)x )?(.*)$')
RE_REF = re.compile(r'^(?:(\d+)x )?ref:no(\d+)$')


def _parse_token(tok_str: str, strings: dict[int, str]) -> str:
    m = RE_LIT.match(tok_str)
    if m:
        return m.group(1)
    m = RE_REF_PREF.match(tok_str)
    if m:
        sid, k = int(m.group(1)), int(m.group(2))
        return strings[sid][:k]
    m = RE_REF_SUF.match(tok_str)
    if m:
        sid, k = int(m.group(1)), int(m.group(2))
        return strings[sid][-k:]
    raise ValueError(f"token desconhecido: {tok_str!r}")


def decode_online(tcf_text: str) -> list[str]:
    strings: dict[int, str] = {}
    body_seq: list[tuple[int, int]] = []
    in_body = False

    for raw in tcf_text.splitlines():
        linha = raw.strip()
        if not linha:
            continue
        if linha == "<body>":
            in_body = True
            continue
        if linha == "</body>":
            in_body = False
            continue
        if not in_body:
            continue

        m = RE_DECL.match(linha)
        if m:
            eid = int(m.group(1))
            count = int(m.group(2)) if m.group(2) else 1
            forma = m.group(3)
            partes = [_parse_token(p, strings) for p in forma.split(' + ')]
            strings[eid] = "".join(partes)
            body_seq.append((eid, count))
            continue

        m = RE_REF.match(linha)
        if m:
            count = int(m.group(1)) if m.group(1) else 1
            eid = int(m.group(2))
            body_seq.append((eid, count))
            continue

        raise ValueError(f"linha mal formada: {linha!r}")

    saida: list[str] = []
    for eid, count in body_seq:
        s = strings[eid]
        saida.extend([s] * count)
    return saida
