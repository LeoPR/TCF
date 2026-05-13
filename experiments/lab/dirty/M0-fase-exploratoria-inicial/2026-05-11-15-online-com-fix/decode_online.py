"""Decoder do formato online (exp 14).

Cada linha decl: 'noN: count_opc forma' onde forma e tokens separados
por ' + '.

Tokens:
  '"X"'             literal
  'noN[0:K]'        primeiros K chars de noN
  'noN[-K:]'        ultimos K chars de noN

Refs: 'ref:noN' ou 'Mx ref:noN'.

Decode em 1 passada — strings sao construidas em ordem, refs a anteriores
ja estao disponiveis.
"""

import re

RE_REF_PREF = re.compile(r'^no(\d+)\[0:(\d+)\]$')
RE_REF_SUF = re.compile(r'^no(\d+)\[-(\d+):\]$')
RE_LIT = re.compile(r'^"(.*)"$')


def decode_online(tcf_text: str) -> list[str]:
    strings: dict[int, str] = {}   # eid -> texto reconstruido
    body_seq: list[tuple[int, int]] = []  # (eid, count) em ordem de aparicao
    estado = "init"

    def parse_token(tok_str: str) -> str:
        """Resolve token para texto. Strings com eid menor ja existem."""
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
            return strings[sid][-k:] if k > 0 else ""
        raise ValueError(f"token desconhecido: {tok_str!r}")

    for raw in tcf_text.splitlines():
        linha = raw.strip()
        if not linha:
            continue
        if linha == "<body>":
            estado = "body"
            continue
        if linha == "</body>":
            estado = "end"
            continue
        if estado != "body":
            continue

        if linha.startswith("no") and ": " in linha:
            # decl externa: "noN: count_opc forma"
            head, sep, rest = linha.partition(": ")
            eid = int(head[2:])
            # count opcional: "Nx forma"
            count_match = re.match(r'^(\d+)x (.*)$', rest)
            if count_match:
                count = int(count_match.group(1))
                forma = count_match.group(2)
            else:
                count = 1
                forma = rest
            # parseia forma: tokens separados por ' + '
            partes = forma.split(' + ')
            partes_texto = [parse_token(p) for p in partes]
            strings[eid] = "".join(partes_texto)
            body_seq.append((eid, count))
        elif linha.startswith("ref:no"):
            eid = int(linha[len("ref:no"):])
            body_seq.append((eid, 1))
        else:
            m = re.match(r'^(\d+)x ref:no(\d+)$', linha)
            if not m:
                raise ValueError(f"linha mal formada: {linha!r}")
            count = int(m.group(1))
            eid = int(m.group(2))
            body_seq.append((eid, count))

    saida: list[str] = []
    for eid, count in body_seq:
        s = strings[eid]
        for _ in range(count):
            saida.append(s)
    return saida
