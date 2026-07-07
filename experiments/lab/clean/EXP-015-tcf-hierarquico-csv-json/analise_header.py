"""analise_header — CONDIÇÕES matemáticas do ganho de fim-de-linha (não um 'quem vence').

Modelo: o meta é a árvore serializada. As DUAS otimizações de fim-de-linha atuam na ÚLTIMA folha (em DFS):
 - última-folha-sem-size: omite `:size` dessa folha → economiza (1 colon + digits(size)).
 - omit-closes: o `\\n` fecha os grupos abertos → economiza os closes finais = **bracket-depth** da última folha.
Logo, escolher qual folha fica por último (via reorder de irmãos, order-free) economiza:
        SAVING(L) = digits(size(L)) + depth(L)          [+1 colon constante]
O ÓTIMO é a folha que maximiza (digits + depth) — **não só profundidade**. O reorder VALE quando a folha
natural-última ≠ argmax. `digits(s)` depende da BASE: decimal len(str(s)) vs HEX len(hex(s)).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codec as C          # noqa: E402


def leaves(node, depth=0):
    """(nome, bracket-depth, [valores]). bracket-depth = nº de grupos {}/[] que envolvem a folha."""
    out = []
    for k, v in node.items():
        if isinstance(v, dict):
            out += leaves(v, depth + 1)
        elif isinstance(v, list):
            for c in (list(v[0]) if v else []):
                out.append((c, depth + 1, [str(r[c]) for r in v]))
        else:
            out.append((k, depth, [str(v)]))
    return out


def dec_dig(s): return len(str(s))
def hex_dig(s): return len(format(s, "x"))


def analyze(tag, doc):
    L = [f"## {tag}", ""]
    lv = leaves(doc)
    # size = bytes do corpo TCF da coluna
    rows = []
    for name, depth, vals in lv:
        size = len(C.encode(vals).encode())
        rows.append((name, depth, size, dec_dig(size), hex_dig(size)))
    L.append(f"  {'folha':10} {'depth':>5} {'size':>5} {'dec':>3} {'hex':>3} {'save_dec':>8} {'save_hex':>8}")
    for name, depth, size, dd, hd in rows:
        L.append(f"  {name:10} {depth:5d} {size:5d} {dd:3d} {hd:3d} {depth+dd:8d} {depth+hd:8d}")
    natural_last = rows[-1]                                   # a última em ordem de inserção
    opt_dec = max(rows, key=lambda r: r[1] + r[3])
    opt_hex = max(rows, key=lambda r: r[1] + r[4])
    s_nat = natural_last[1] + natural_last[3]
    L += ["",
          f"  natural-última: {natural_last[0]}  → save={s_nat}",
          f"  ÓTIMO (dec):    {opt_dec[0]}  → save={opt_dec[1]+opt_dec[3]}   reorder vale? {opt_dec[1]+opt_dec[3] > s_nat} (Δ={opt_dec[1]+opt_dec[3]-s_nat:+d}B)",
          f"  ÓTIMO (hex):    {opt_hex[0]}  → save={opt_hex[1]+opt_hex[4]}   (hex muda o argmax? {opt_hex[0] != opt_dec[0]})",
          f"  soma de digits no header TODO: dec={sum(r[3] for r in rows)}  hex={sum(r[4] for r in rows)}  (hex economiza {sum(r[3]-r[4] for r in rows)}B nos sizes)",
          ""]
    return "\n".join(L)


def main():
    out = ["# CONDIÇÕES do ganho de fim-de-linha — SAVING(L) = digits(size(L)) + depth(L)", "",
           "Não é 'quem vence': é a SITUAÇÃO. O ótimo maximiza (digits + depth) da última folha; o reorder",
           "só vale se a folha natural-última ≠ argmax. Hex muda digits(size) (e pode mudar o argmax).", ""]

    # caso 1: S6 (a situação onde a natural já é ótima — por acaso tel tem size grande)
    s6 = json.loads((Path(__file__).resolve().parent / "inputs" / "S6-pessoa-endereco-geo.json").read_text(encoding="utf-8"))
    out.append(analyze("S6 (natural já ótima → reorder NÃO ajuda)", s6))

    # caso 2: construído — folha profunda E grande NÃO está por último → reorder ganha
    win = {"grp": {"sub": {"big": "x" * 130}}, "z": "ab"}     # big: depth 2, size ~132 (3 dec dig)
    out.append(analyze("WIN construído (big profundo+grande, mas z é a última) → reorder GANHA", win))

    # caso 3: hex — size na faixa [100-255] (dec 3, hex 2) e [10-15] (dec 2, hex 1)
    hexcase = {"a": "y" * 200, "b": "z" * 12, "c": "w"}       # a size~202 (dec3/hex2), b size~14 (dec2/hex1)
    out.append(analyze("HEX construído (sizes em [100-255] e [10-15]) → hex economiza digits", hexcase))

    out += ["## Condições (o resumo matemático)",
            "1. **omit-closes**: SEMPRE bom (economiza depth(última) closes; RT-exato). Independe de tudo.",
            "2. **reorder profundo-por-último**: vale SSE `argmax_L(digits(size L)+depth L) ≠ natural-última`.",
            "   NÃO é só profundidade — é **digits+depth**. Uma folha rasa mas de size grande (muitos digits)",
            "   pode ganhar de uma profunda de size pequeno. Em S6 empata (tel: depth1+2dig=3 = lat/lon/rua).",
            "3. **hex nos sizes**: digits_hex(s)=len(hex(s)) < len(str(s)) para s∈[10,15]∪[100,255]∪[256,4095]…",
            "   Ganha nas fronteiras 16ᵏ vs 10ᵏ. Afeta o header TODO (cada size) E pode mudar o argmax do reorder.",
            "   (para s∈[16,99] empata: 2 dígitos nos dois; <10 empata: 1.)",
            "→ Nenhuma otimização 'vence' sempre; o ganho é uma CONTA: escolher a última folha que maximiza",
            "  digits(size)+depth, com digits na base (dec/hex) que minimiza o total. É config-dependente."]
    Path(Path(__file__).resolve().parent / "outputs" / "05-header-condicoes.txt").write_text(
        "\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
