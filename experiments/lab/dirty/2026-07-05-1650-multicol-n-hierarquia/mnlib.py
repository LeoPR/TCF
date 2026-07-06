"""mnlib — engenhoca (descartável): modelo "multi-col + marcador N" (a ideia MAIS SIMPLES do owner).

NÃO são blocos empilhados com header de linking (isso é a peça 3). Aqui é **a estrutura multi-col que já
existe**, só com um COMPLEMENTO BARATO:
  1) flag `N` no shebang (`#TCF.8 M N`) — irmão do flag `M`;
  2) uma linha de HIERARQUIA `#H ...` que reagrupa as colunas (que já vêm em ORDEM) na árvore.
As colunas continuam nomeadas (obrigatório — o nome aparece na referência principal / meta), agrupadas
pela ordem; a hierarquia é o "complemento que explica". Colunas podem ter comprimentos diferentes
(raiz escalar = 1 linha; array = N linhas) — o `N` sinaliza isso; o byte-size do meta delimita.

Notação #H (draft):  escalar = `nome` · objeto = `nome{ ... }` · array-de-objetos = `nome[ col1 col2 ]`.
Ex.: `nome telefones[tel]` · `nome endereco{rua cidade geo{lat lon}} telefones[tel]`.

Simplificação desta peça: valores tratados como STRING (as fixtures são all-string). Tipos (num/bool/null)
seriam um `:tipo` por coluna, como na peça 3 — deixado de fora pra "começar muito mais simples".
"""
from __future__ import annotations

SHEBANG = "#TCF.8 M N"


# ---- doc → hierarquia (#H) + colunas (ordem DFS) ----
def hspec(node: dict) -> str:
    parts = []
    for k, v in node.items():
        if isinstance(v, dict):
            parts.append(f"{k}{{{hspec(v)}}}")
        elif isinstance(v, list):
            cols = list(v[0]) if v else []
            parts.append(f"{k}[{' '.join(cols)}]")
        else:
            parts.append(k)
    return " ".join(parts)


def columns(node: dict):
    """Lista ordenada (DFS) de (nome_coluna, [valores-string]). Casa 1:1 com a ordem do #H."""
    cols = []
    for k, v in node.items():
        if isinstance(v, dict):
            cols += columns(v)
        elif isinstance(v, list):
            elcols = list(v[0]) if v else []
            for c in elcols:
                cols.append((c, [str(r[c]) for r in v]))
        else:
            cols.append((k, [str(v)]))
    return cols


# ---- encode: 1 TCF multi-col (ragged) + #H ----
def encode_mn(doc: dict, encode) -> str:
    h = hspec(doc)
    cols = columns(doc)
    bodies = [encode(vals) for (_n, vals) in cols]     # corpo órfão single-col por coluna
    metaparts = []
    for i, ((name, _vals), body) in enumerate(zip(cols, bodies)):
        metaparts.append(name if i == len(cols) - 1 else f"{len(body.encode())}={name}")
    meta = ",".join(metaparts)
    return f"{SHEBANG}\n#H {h}\n{meta}\n" + "".join(bodies)


# ---- decode: split por bytes → colunas → reagrupa pela #H ----
def _parse_hspec(s: str):
    pos = 0

    def seq(closing):
        nonlocal pos
        fields = []
        while pos < len(s):
            while pos < len(s) and s[pos] == " ":
                pos += 1
            if pos >= len(s) or (closing and s[pos] == closing):
                if closing and pos < len(s) and s[pos] == closing:
                    pos += 1
                break
            j = pos
            while pos < len(s) and s[pos] not in " {}[]":
                pos += 1
            name = s[j:pos]
            while pos < len(s) and s[pos] == " ":
                pos += 1
            if pos < len(s) and s[pos] == "{":
                pos += 1
                fields.append(("obj", name, seq("}")))
            elif pos < len(s) and s[pos] == "[":
                pos += 1
                cnames = []
                while pos < len(s) and s[pos] != "]":
                    while pos < len(s) and s[pos] == " ":
                        pos += 1
                    j2 = pos
                    while pos < len(s) and s[pos] not in " ]":
                        pos += 1
                    if pos > j2:
                        cnames.append(s[j2:pos])
                if pos < len(s) and s[pos] == "]":
                    pos += 1
                fields.append(("arr", name, cnames))
            else:
                fields.append(("scalar", name, None))
        return fields

    return seq(None)


def decode_mn(text: str, decode) -> dict:
    shebang, hline, meta, rest = text.split("\n", 3)
    assert shebang == SHEBANG, f"shebang inesperado: {shebang!r}"
    assert hline.startswith("#H "), f"esperava linha #H: {hline!r}"
    h = hline[3:]
    # meta: 'size=name,...,name' (último sem size, estilo multi-col)
    entries = meta.split(",")
    sn = []
    for i, e in enumerate(entries):
        if i < len(entries) - 1 and "=" in e:
            sz, nm = e.split("=", 1)
            sn.append((int(sz), nm))
        else:
            sn.append((None, e))
    raw = rest.encode("utf-8")
    cols, off = {}, 0
    for sz, nm in sn:
        body = raw[off:].decode("utf-8") if sz is None else raw[off:off + sz].decode("utf-8")
        if sz is not None:
            off += sz
        cols[nm] = decode(body)

    def rebuild(fields):
        out = {}
        for kind, name, payload in fields:
            if kind == "scalar":
                out[name] = cols[name][0]
            elif kind == "obj":
                out[name] = rebuild(payload)
            else:  # arr
                cn = payload
                n = len(cols[cn[0]]) if cn else 0
                out[name] = [{c: cols[c][i] for c in cn} for i in range(n)]
        return out

    return rebuild(_parse_hspec(h))
