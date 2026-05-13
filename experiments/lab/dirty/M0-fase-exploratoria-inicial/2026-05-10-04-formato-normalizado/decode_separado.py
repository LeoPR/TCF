"""Decoder do formato separado normalizado."""

import re

RE_DECL_FOLHA = re.compile(r'^no(\d+)\s*=\s*folha\s*"(.*)"$')
RE_DECL_FILHO = re.compile(
    r'^no(\d+)\s*=\s*filho_de\(no(\d+)\)\s*\+\s*"(.*)"$'
)
RE_REF = re.compile(r'^(?:(\d+)x\s+)?ref:no(\d+)$')


def decode_separado(tcf_text: str) -> list[str]:
    nos: dict[int, tuple[int | None, str]] = {}
    body_seq: list[tuple[int, int]] = []
    estado = "init"

    for raw in tcf_text.splitlines():
        linha = raw.strip()
        if not linha:
            continue
        if linha == "<patricia>":
            estado = "patricia"
            continue
        if linha == "</patricia>":
            estado = "between"
            continue
        if linha == "<body>":
            estado = "body"
            continue
        if linha == "</body>":
            estado = "end"
            continue

        if estado == "patricia":
            m = RE_DECL_FOLHA.match(linha)
            if m:
                nos[int(m.group(1))] = (None, m.group(2))
                continue
            m = RE_DECL_FILHO.match(linha)
            if m:
                nos[int(m.group(1))] = (int(m.group(2)), m.group(3))
                continue
            raise ValueError(f"linha patricia mal formada: {linha!r}")

        if estado == "body":
            m = RE_REF.match(linha)
            if not m:
                raise ValueError(f"linha body mal formada: {linha!r}")
            count = int(m.group(1)) if m.group(1) else 1
            body_seq.append((int(m.group(2)), count))

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
