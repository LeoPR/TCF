"""Lab 2026-07-24-2210 — null como INDICE 0 numa coluna de string (protótipo).

Escala do owner: **uma coluna de UM tipo**. `[null, "", "true", "false", "oi", null, "null"]`
é uma coluna de STRING onde null é um token válido — a falta do dado, não outro tipo.

  HOJE      a coluna é EXPULSA do flat pro `.8H` (porque `None` não é `str`) e o null vira
            máscara def-level num canal `?` separado.
  PROTOTIPO a coluna FICA no flat `#TCF.8`; o null é referência ao índice 0 da tabela, que
            nasce PRÉ-SEMEADA (plano `substituicao-indices-especiais-plano.md`).

O índice 0 está livre: a string literal "0" é escapada como `\\0`, então um `0` puro no corpo
nunca é literal — é sempre referência. Confirmado empiricamente (§ colisão).

ARQUITETURA DO PROTOTIPO (modelo do owner, camada explícita ↔ implícita): o decoder é um
PRE-AVALIADOR que expande `0` (implícito) pro literal (explícito) e delega ao core REAL,
intocado. Por isso o RT é fiel — não há reimplementação do compressor aqui.
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import encode, decode  # noqa: E402

MARCA = "0"          # placeholder textual = a grafia que o índice reservado terá no wire
CAB = "#TCF.8\n"


# ============================================================ protótipo: encode / decode
def _split(ln):
    """`*N|resto` -> ('*N|', resto); senão ('', ln)."""
    if ln.startswith("*") and "|" in ln:
        bar = ln.find("|")
        return ln[:bar + 1], ln[bar + 1:]
    return "", ln


def enc_proto(col):
    """Coluna (str|None) -> wire `#TCF.8` com null como `0` = ENDEREÇO RESERVADO.

    Grafia decidida pelo owner (2026-07-24, revisão): o `0` cru é a *representação otimizada*
    de `^0` — logo herda a SEMÂNTICA do `^0`: **não declara nó**. Assim TODO null é `0` (1
    char), em vez de o 1º declarar e os demais virarem `^k`. Medido −479 B em 17 casos contra
    a grafia que declarava. Ver `colisao-e-grafia-final.py`.

    Desambiguação POSICIONAL (mesma classe do char de modo no índice 7): a **linha inteira**
    igual a `0` é o especial; um `0` dentro de composição (`1~0`) segue sendo FRAGMENTO.

    TRUQUE (não é reimplementação): passa a coluna pro encode REAL com null trocado por "0";
    o core escapa como `\\0` e resolve repetições sozinho. Como `0` não declara nó, os nós
    reais renumeram para baixo.
    """
    if any(v == MARCA for v in col if v is not None):
        raise ValueError("coluna contém a string '0' — colidiria com o placeholder do protótipo")
    linhas = encode([MARCA if v is None else v for v in col], stamp=False).split("\n")
    z, no = None, 0                                   # z = nó que a declaração do null ocuparia
    for ln in linhas:
        _pre, r = _split(ln)
        if r.startswith("^") or ln == "":
            continue
        no += 1
        if r == "\\0":
            z = no
    out = []
    for ln in linhas:
        pre, r = _split(ln)
        if r == "\\0":
            out.append(pre + "0")                     # declaração -> endereço reservado
        elif r.startswith("^"):
            k = int(r[1:])
            out.append(pre + ("0" if k == z else f"^{k - 1 if z and k > z else k}"))
        else:
            out.append(ln)
    return CAB + "\n".join(out)


def dec_proto(wire):
    """Pré-avaliador: `0` (otimizado) -> `^0` -> forma explícita -> core REAL -> None."""
    if not wire.startswith(CAB):
        raise ValueError("wire do protótipo sem cabeçalho #TCF.8")
    linhas = wire[len(CAB):].split("\n")
    m = 0                                             # nós declarados ANTES do 1º `0`
    for ln in linhas:
        _pre, r = _split(ln)
        if r == "0":
            break
        if r.startswith("^") or ln == "":
            continue
        m += 1
    z, visto, out = m + 1, False, []
    for ln in linhas:
        pre, r = _split(ln)
        if r == "0":
            out.append(pre + ("\\0" if not visto else f"^{z}"))
            visto = True
        elif r.startswith("^"):
            k = int(r[1:])
            out.append(pre + f"^{k + 1 if k >= z else k}")
        else:
            out.append(ln)
    return [None if v == MARCA else v for v in decode("\n".join(out))]


# ============================================================ datasets
def _gera(n, pct, seed=7):
    """Coluna realista de baixa cardinalidade com `pct`% de null (LCG determinístico)."""
    vocab = ["ativo", "inativo", "pendente", "revisao", "cancelado"]
    out, x = [], seed
    for i in range(n):
        x = (1103515245 * x + 12345) % (2 ** 31)
        out.append(None if (x % 100) < pct else vocab[i % len(vocab)])
    return out


FONTES = {
    "A-exemplo-owner": ([None, "", "true", "false", "oi", None, "null"],
                        "o exemplo literal do owner — 4 vias numa coluna de string"),
    "B-n7-1null":      ([None, "ativo", "inativo", "ativo", "pendente", "ativo", "inativo"],
                        "n pequeno, 1 null"),
    "C-todos-null":    ([None] * 12, "coluna 100% null (borda)"),
    "D-null-bordas":   ([None, "a", "b", "c", None], "null na primeira e na última posição"),
    "E-sem-null":      (["ativo", "inativo", "ativo", "pendente"],
                        "CONTROLE: sem null -> protótipo tem que ser byte-idêntico ao flat"),
}
for _n in (10, 100, 1000):
    for _p in (1, 10, 50, 90):
        FONTES[f"R-n{_n}-p{_p}"] = (_gera(_n, _p), f"regime n={_n}, {_p}% null")


def _w(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ============================================================ execução
def main():
    linhas, falhas, ctrl_ok = [], 0, None
    for eid, (col, nota) in FONTES.items():
        _w(RAIZ / "inputs" / f"{eid}-fonte.json", {"nota": nota, "dados": col})
        _w(RAIZ / "intermediates" / f"{eid}-dataset-consumido.json", col)

        w_hoje = encode(col)                       # REAL (rota .8H por causa do None)
        w_prot = enc_proto(col)                    # PROTOTIPO
        rt_hoje = decode(w_hoje) == col
        rt_prot = dec_proto(w_prot) == col
        falhas += (not rt_hoje) + (not rt_prot)

        if eid == "E-sem-null":                    # controle de byte-neutralidade
            ctrl_ok = (w_prot == encode(col))

        (RAIZ / "outputs" / f"{eid}-hoje.tcf").write_text(w_hoje, encoding="utf-8")
        (RAIZ / "outputs" / f"{eid}-proto.tcfp").write_text(w_prot, encoding="utf-8")
        _w(RAIZ / "outputs" / f"{eid}-dataset.roundtrip.json", dec_proto(w_prot))

        a, b = len(w_hoje.encode()), len(w_prot.encode())
        linhas.append((eid, len(col), sum(v is None for v in col), a, b,
                       b - a, 100 * (b - a) / a, "OK" if (rt_hoje and rt_prot) else "FALHOU"))

    out = ["# Resultado — null como índice 0 numa coluna de string (2026-07-24-2210)", "",
           "`hoje` = `src/tcf` REAL (rota `.8H`, máscara). `proto` = flat `#TCF.8` + índice 0.", "",
           "| id | n | nulls | hoje (B) | proto (B) | Δ | Δ% | RT |",
           "|---|---:|---:|---:|---:|---:|---:|---|"]
    out += [f"| {e} | {n} | {k} | {a} | {b} | {d:+} | {p:+.0f}% | {s} |"
            for e, n, k, a, b, d, p, s in linhas]

    ganhos = [p for *_, p, s in linhas if s == "OK"]
    out += ["", f"RT: **{len(linhas) - falhas}/{len(linhas)}** ok "
                f"(hoje E protótipo, os dois validados).",
            f"CONTROLE sem-null byte-idêntico ao flat: **{'SIM' if ctrl_ok else 'NAO'}** "
            f"— o protótipo não cobra de quem não tem null.",
            f"Δ mediano: **{sorted(ganhos)[len(ganhos) // 2]:+.0f}%**", ""]

    # ---- DECOMPOSIÇÃO: o ganho vem do envelope ou do índice? (auto-adversarial)
    out += ["## Decomposição — de onde vem o ganho", "",
            "- **(a) hoje** = `.8H` + máscara (real)",
            "- **(b) flat+literal** = flat com null → literal `\"0\"` — **NÃO-lossless** "
            "(colide com a string real `\"0\"`)",
            "- **(c) protótipo** = flat + índice 0 reservado — lossless", "",
            "| caso | (a) | (b) | (c) | envelope (a−b) | índice (b−c) |",
            "|---|---:|---:|---:|---:|---:|"]
    te = ti = 0
    for eid, (col, _n) in FONTES.items():
        if not any(v is None for v in col):
            continue
        a = len(encode(col).encode())
        b = len(encode([MARCA if v is None else v for v in col], stamp=False).encode()) + len(CAB)
        c = len(enc_proto(col).encode())
        te += a - b
        ti += b - c
        out.append(f"| {eid} | {a} | {b} | {c} | {a - b:+} | {b - c:+} |")
    out += [f"| **TOTAL** | | | | **{te:+}** | **{ti:+}** |", "",
            f"Do ganho total de {te + ti} B: **envelope = {100 * te / (te + ti):.0f}%**, "
            f"**índice = {100 * ti / (te + ti):.0f}%**.", "",
            "A parcela do índice cresceu com a grafia decidida pelo owner (`0` como endereço "
            "reservado que NÃO declara nó): **todo** null vira 1 char, contra 2 do literal "
            "`\\0` e 2+ do `^k` que a grafia anterior gerava nas repetições. Por isso ela "
            "escala com a densidade de null (+249 B em `R-n1000-p50`).", "",
            "**Mas o valor estrutural do índice não é essa parcela.** A forma (b), que sozinha "
            "captura a maior parte, é **inviável**: um literal colide com a string real `\"0\"` "
            "— foi exatamente a refutação do lab `2026-07-13-1921`. O índice reservado é o que "
            "torna ficar no flat **lossless**; ele não só gera ganho, ele **VIABILIZA** o resto.", ""]

    out += ["## Wire lado a lado — exemplo do owner", ""]
    col = FONTES["A-exemplo-owner"][0]
    out += [f"```\ncoluna : {col}",
            f"hoje   : {encode(col)!r}",
            f"proto  : {enc_proto(col)!r}\n```", ""]
    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    # console do Windows e' cp1252 e engasga em 'Δ'; o result.md sai em UTF-8 intacto
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("\n".join(out))
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
