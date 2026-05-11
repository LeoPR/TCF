"""TCF demonstrativo -> lista de strings (uma por linha original).

Decode independente do encode: parseia somente o que esta no arquivo
e reconstrutruir as folhas via cadeia pai+sufixo.
"""

import re


def decode(tcf_text: str) -> tuple[str, list[str]]:
    nos: dict[int, tuple[int | None, str]] = {}
    body_rle: list[tuple[int, int]] = []
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
            m = re.match(r'no(\d+)\s*=\s*folha\s*"(.*)"$', linha)
            if m:
                nos[int(m.group(1))] = (None, m.group(2))
                continue
            m = re.match(
                r'no(\d+)\s*=\s*filho_de\(no(\d+)\)\s*\+\s*"(.*)"$', linha
            )
            if m:
                nos[int(m.group(1))] = (int(m.group(2)), m.group(3))
                continue
            raise ValueError(f"linha patricia mal formada: {linha!r}")

        if estado == "body":
            m = re.match(r"(?:(\d+)x\s+)?ref:no(\d+)$", linha)
            if not m:
                raise ValueError(f"linha body mal formada: {linha!r}")
            rep = int(m.group(1)) if m.group(1) else 1
            no_id = int(m.group(2))
            body_rle.append((no_id, rep))

    def texto(no_id: int) -> str:
        pai_id, frag = nos[no_id]
        if pai_id is None:
            return frag
        return texto(pai_id) + frag

    saida: list[str] = []
    for no_id, rep in body_rle:
        s = texto(no_id)
        for _ in range(rep):
            saida.append(s)
    return header_col, saida
