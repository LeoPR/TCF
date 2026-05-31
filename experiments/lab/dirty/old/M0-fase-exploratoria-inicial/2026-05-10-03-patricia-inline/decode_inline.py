"""Decodificador inline em 2 passadas.

Pass 1: parseia todas as linhas, registra nos (forma + pai_emit_id) e
        a sequencia de ocorrencias. Forward refs ficam pendentes.
Pass 2: reconstroi texto de cada no via cadeia pai+sufixo. Os forward
        refs resolvem porque todos os nos foram registrados antes.
"""

import re

RE_DECL_FOLHA_OCC = re.compile(
    r'^no(\d+):\s*(\d+)x\s*folha\s*"(.*)"$'
)
RE_DECL_FILHO_OCC = re.compile(
    r'^no(\d+):\s*(\d+)x\s*filho_de\(no(\d+)\)\s*\+\s*"(.*)"$'
)
RE_DECL_FOLHA_TARDIA = re.compile(
    r'^no(\d+):\s*decl\s*folha\s*"(.*)"$'
)
RE_DECL_FILHO_TARDIA = re.compile(
    r'^no(\d+):\s*decl\s*filho_de\(no(\d+)\)\s*\+\s*"(.*)"$'
)
RE_REF = re.compile(r'^(\d+)x\s+ref:no(\d+)$')


def decode_inline(tcf_text: str) -> tuple[str, list[str]]:
    nos: dict[int, tuple[int | None, str]] = {}  # eid -> (pai_eid, fragmento)
    body_seq: list[tuple[int, int]] = []         # [(eid, count), ...]
    header_col = ""
    estado = "header"

    for raw in tcf_text.splitlines():
        linha = raw.strip()
        if not linha:
            continue
        if linha.startswith("# coluna:"):
            header_col = linha.split(":", 1)[1].strip()
            continue
        if linha.startswith("#"):
            continue
        if linha == "<body>":
            estado = "body"
            continue
        if linha == "</body>":
            estado = "end"
            continue

        if estado != "body":
            continue

        m = RE_DECL_FOLHA_OCC.match(linha)
        if m:
            eid, count, frag = int(m.group(1)), int(m.group(2)), m.group(3)
            nos[eid] = (None, frag)
            body_seq.append((eid, count))
            continue

        m = RE_DECL_FILHO_OCC.match(linha)
        if m:
            eid = int(m.group(1))
            count = int(m.group(2))
            pai_eid = int(m.group(3))
            frag = m.group(4)
            nos[eid] = (pai_eid, frag)
            body_seq.append((eid, count))
            continue

        m = RE_DECL_FOLHA_TARDIA.match(linha)
        if m:
            eid, frag = int(m.group(1)), m.group(2)
            nos[eid] = (None, frag)
            continue

        m = RE_DECL_FILHO_TARDIA.match(linha)
        if m:
            eid = int(m.group(1))
            pai_eid = int(m.group(2))
            frag = m.group(3)
            nos[eid] = (pai_eid, frag)
            continue

        m = RE_REF.match(linha)
        if m:
            count, eid = int(m.group(1)), int(m.group(2))
            body_seq.append((eid, count))
            continue

        raise ValueError(f"linha mal formada: {linha!r}")

    # Pass 2: reconstroi texto via cadeia
    cache: dict[int, str] = {}

    def texto(eid: int) -> str:
        if eid in cache:
            return cache[eid]
        if eid not in nos:
            raise ValueError(f"forward ref nao resolvida: no{eid}")
        pai_eid, frag = nos[eid]
        t = frag if pai_eid is None else texto(pai_eid) + frag
        cache[eid] = t
        return t

    saida: list[str] = []
    for eid, count in body_seq:
        s = texto(eid)
        for _ in range(count):
            saida.append(s)
    return header_col, saida
