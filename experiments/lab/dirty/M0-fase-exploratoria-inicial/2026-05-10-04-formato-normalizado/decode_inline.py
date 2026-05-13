"""Decoder do formato inline normalizado.

count opcional (omitido => 1) em decls inline e em refs.
"""

import re

RE_DECL_FOLHA_OCC = re.compile(
    r'^no(\d+):\s*(?:(\d+)x\s+)?folha\s*"(.*)"$'
)
RE_DECL_FILHO_OCC = re.compile(
    r'^no(\d+):\s*(?:(\d+)x\s+)?filho_de\(no(\d+)\)\s*\+\s*"(.*)"$'
)
RE_DECL_FOLHA_TARDIA = re.compile(
    r'^no(\d+):\s*decl\s+folha\s*"(.*)"$'
)
RE_DECL_FILHO_TARDIA = re.compile(
    r'^no(\d+):\s*decl\s+filho_de\(no(\d+)\)\s*\+\s*"(.*)"$'
)
RE_REF = re.compile(r'^(?:(\d+)x\s+)?ref:no(\d+)$')


def decode_inline(tcf_text: str) -> list[str]:
    nos: dict[int, tuple[int | None, str]] = {}
    body_seq: list[tuple[int, int]] = []
    estado = "init"

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

        # tardias antes (mais especificas)
        m = RE_DECL_FOLHA_TARDIA.match(linha)
        if m:
            nos[int(m.group(1))] = (None, m.group(2))
            continue
        m = RE_DECL_FILHO_TARDIA.match(linha)
        if m:
            nos[int(m.group(1))] = (int(m.group(2)), m.group(3))
            continue

        m = RE_DECL_FOLHA_OCC.match(linha)
        if m:
            eid = int(m.group(1))
            count = int(m.group(2)) if m.group(2) else 1
            nos[eid] = (None, m.group(3))
            body_seq.append((eid, count))
            continue
        m = RE_DECL_FILHO_OCC.match(linha)
        if m:
            eid = int(m.group(1))
            count = int(m.group(2)) if m.group(2) else 1
            nos[eid] = (int(m.group(3)), m.group(4))
            body_seq.append((eid, count))
            continue

        m = RE_REF.match(linha)
        if m:
            count = int(m.group(1)) if m.group(1) else 1
            body_seq.append((int(m.group(2)), count))
            continue

        raise ValueError(f"linha mal formada: {linha!r}")

    cache: dict[int, str] = {}

    def texto(eid: int) -> str:
        if eid in cache:
            return cache[eid]
        pai_eid, frag = nos[eid]
        t = frag if pai_eid is None else texto(pai_eid) + frag
        cache[eid] = t
        return t

    saida: list[str] = []
    for eid, count in body_seq:
        s = texto(eid)
        for _ in range(count):
            saida.append(s)
    return saida
