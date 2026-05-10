"""Lab 23: validacao em escala (>= 100 valores).

Reusa encoder do lab 18 (PATRICIA + inline) que foi o melhor agregado.

Cenarios escalonados:
  E1: 100 emails 1 dominio
  E2: 1000 emails 1 dominio
  E3: 100 codigos PED
  E4: 1000 codigos PED
  E5: 100 categoricas em 5 unicos
  E6: 500 misturados (codigos + emails + nomes)
  E7: 1000 URLs com subpath

Compara TCF v0.5 (lab 18 engine) vs CSV vs CSV+gzip.

Saida: ./output/
"""
from __future__ import annotations
import gzip
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)


def gz(text):
    return gzip.compress(text.encode("utf-8"), compresslevel=9)


# ---------------------------------------------------------------------------
# Encoder (do lab 18 — PATRICIA + inline) — reuso
# ---------------------------------------------------------------------------

class PatNode:
    __slots__ = ("label", "children", "terminal_lines")
    def __init__(self, label=""):
        self.label = label
        self.children: list[PatNode] = []
        self.terminal_lines: list[int] = []


def lcp_str(a, b):
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return i


def insert(root, value, line_idx):
    node = root
    while True:
        if not value:
            node.terminal_lines.append(line_idx)
            return
        match = None
        for c in node.children:
            if c.label and c.label[0] == value[0]:
                match = c
                break
        if match is None:
            new_node = PatNode(value)
            new_node.terminal_lines.append(line_idx)
            node.children.append(new_node)
            return
        l = lcp_str(match.label, value)
        if l == len(match.label):
            node = match
            value = value[l:]
            continue
        common = match.label[:l]
        old_rest = match.label[l:]
        new_rest = value[l:]
        intermediate = PatNode(common)
        match.label = old_rest
        intermediate.children.append(match)
        if new_rest:
            new_n = PatNode(new_rest)
            new_n.terminal_lines.append(line_idx)
            intermediate.children.append(new_n)
        else:
            intermediate.terminal_lines.append(line_idx)
        idx = node.children.index(match)
        node.children[idx] = intermediate
        return


def count_terminals(node):
    c = len(node.terminal_lines)
    for ch in node.children:
        c += count_terminals(ch)
    return c


def collect_with_gain(root, min_count=2, min_len=4):
    out = []
    def dfs(n, acc=""):
        full = acc + n.label
        if full and len(full) >= min_len:
            ct = count_terminals(n)
            if ct >= min_count:
                gain = ct * (len(full) - 1) - (len(full) + 2)
                if gain > 0:
                    out.append((full, ct, gain))
        for ch in n.children:
            dfs(ch, full)
    dfs(root)
    out.sort(key=lambda x: -x[2])
    return out


def encode(values):
    if not values:
        return ""

    fwd = PatNode()
    for i, v in enumerate(values, 1):
        insert(fwd, v, i)
    prefix_cands = collect_with_gain(fwd)

    rev_root = PatNode()
    for i, v in enumerate(values, 1):
        insert(rev_root, v[::-1], i)
    suffix_cands_rev = collect_with_gain(rev_root)
    suffix_cands = [(s[::-1], c, g) for s, c, g in suffix_cands_rev]

    decompositions = []
    for v in values:
        best_p = ""
        best_p_gain = 0
        for p, _, gain in prefix_cands:
            if v.startswith(p) and gain > best_p_gain:
                best_p = p
                best_p_gain = gain
        rest = v[len(best_p):] if best_p else v
        best_s = ""
        best_s_gain = 0
        for s, _, gain in suffix_cands:
            if rest.endswith(s) and gain > best_s_gain:
                best_s = s
                best_s_gain = gain
        mid = rest[:-len(best_s)] if best_s else rest
        decompositions.append((best_p, mid, best_s))

    declared: dict[str, int] = {}
    line_history: dict[str, int] = {}
    out = []

    for line_no, (v, (best_p, mid, best_s)) in enumerate(zip(values, decompositions), 1):
        if v in line_history:
            out.append(f"={line_history[v]}")
            continue
        line_history[v] = line_no

        tokens = []
        if best_p:
            if best_p in declared:
                tokens.append(str(declared[best_p]))
            else:
                declared[best_p] = len(declared) + 1
                tokens.append(f"*{best_p}")
        if mid:
            if mid.isdigit():
                tokens.append(f"_{mid}")
            else:
                tokens.append(mid)
        if best_s:
            if best_s in declared:
                tokens.append(str(declared[best_s]))
            else:
                declared[best_s] = len(declared) + 1
                tokens.append(f"*{best_s}")
        if not tokens:
            tokens.append(f"_{v}" if v.isdigit() else v)
        out.append(" ".join(tokens))

    return "\n".join(out) + "\n"


def decode(text):
    lines = text.splitlines()
    string_dict: list[str] = []
    line_history: list[str] = []
    out = []
    for line in lines:
        if not line:
            continue
        if line.startswith("="):
            ref = int(line[1:])
            v = line_history[ref - 1]
        else:
            tokens = line.split(" ")
            parts = []
            for tok in tokens:
                if tok.startswith("*"):
                    txt = tok[1:]
                    string_dict.append(txt)
                    parts.append(txt)
                elif tok.startswith("_"):
                    parts.append(tok[1:])
                elif tok.isdigit():
                    parts.append(string_dict[int(tok) - 1])
                else:
                    parts.append(tok)
            v = "".join(parts)
        out.append(v)
        line_history.append(v)
    return out


# ---------------------------------------------------------------------------
# Cenarios escala
# ---------------------------------------------------------------------------

def E1_emails_100():
    return [f"user{i:03d}@gmail.com" for i in range(100)]


def E2_emails_1000():
    return [f"user{i:04d}@gmail.com" for i in range(1000)]


def E3_codigos_100():
    return [f"PED-2026-{i:04d}" for i in range(1, 101)]


def E4_codigos_1000():
    return [f"PED-2026-{i:05d}" for i in range(1, 1001)]


def E5_categoricas_100():
    cats = ["red", "blue", "green", "yellow", "purple"]
    random.seed(42)
    return [random.choice(cats) for _ in range(100)]


def E6_misturado_500():
    """500 strings misturadas: codigos + emails + nomes."""
    random.seed(42)
    out = []
    nomes = ["Ana", "Bruno", "Carlos", "Diana", "Eduardo", "Fernanda"]
    for i in range(500):
        choice = random.choice(["code", "email", "name"])
        if choice == "code":
            out.append(f"INV-2026-{i:05d}")
        elif choice == "email":
            out.append(f"user{i:04d}@gmail.com")
        else:
            out.append(f"{random.choice(nomes)}_{i:03d}")
    return out


def E7_urls_1000():
    base = "https://api.example.com"
    paths = ["users", "orders", "products", "events", "metrics"]
    out = []
    for i in range(1000):
        out.append(f"{base}/v1/{random.choice(paths)}/{i:04d}")
    random.seed(42)
    random.shuffle(out)
    return out


SCENARIOS = [
    ("E1-emails-100",       E1_emails_100()),
    ("E2-emails-1000",      E2_emails_1000()),
    ("E3-codigos-100",      E3_codigos_100()),
    ("E4-codigos-1000",     E4_codigos_1000()),
    ("E5-categoricas-100",  E5_categoricas_100()),
    ("E6-misturado-500",    E6_misturado_500()),
    ("E7-urls-1000",        E7_urls_1000()),
]


def main():
    print("=" * 96)
    print("Lab 23: validacao em escala (>=100 valores)")
    print("=" * 96)

    all_results = []

    for name, values in SCENARIOS:
        print("\n" + "=" * 96)
        print(f"[{name}] {len(values)} valores")
        print("=" * 96)

        scen = OUT / name
        scen.mkdir(exist_ok=True)

        literal = "\n".join(values) + "\n"
        b_lit = len(literal.encode("utf-8"))
        b_lit_gz = len(gz(literal))

        text = encode(values)
        b_tcf = len(text.encode("utf-8"))
        b_tcf_gz = len(gz(text))

        try:
            decoded = decode(text)
            rt = decoded == values
            err = None
        except Exception as e:
            rt = False
            err = f"{type(e).__name__}: {e}"

        # Salva (so 1a + ultima + meio para nao explodir)
        (scen / "literal.txt").write_text(literal[:5000] + ("\n... (truncado)" if len(literal) > 5000 else ""), encoding="utf-8")
        (scen / "tcf.txt").write_text(text[:5000] + ("\n... (truncado)" if len(text) > 5000 else ""), encoding="utf-8")

        # Comparacoes
        v_lit = (b_tcf/b_lit-1)*100
        v_lit_gz = (b_tcf_gz/b_lit_gz-1)*100

        sign1 = "+" if v_lit >= 0 else ""
        sign2 = "+" if v_lit_gz >= 0 else ""

        print(f"\n  N={len(values)}")
        print(f"  literal:   {b_lit:>7}B  +gz: {b_lit_gz:>5}")
        print(f"  TCF:       {b_tcf:>7}B  +gz: {b_tcf_gz:>5}")
        print(f"  TCF vs literal:        {sign1}{v_lit:>+6.1f}%")
        print(f"  TCF+gz vs literal+gz:  {sign2}{v_lit_gz:>+6.1f}%")
        print(f"  rt: {'OK' if rt else 'FAIL'}{' — '+err if err else ''}")

        all_results.append({
            "name": name, "n": len(values),
            "literal": b_lit, "literal_gz": b_lit_gz,
            "tcf": b_tcf, "tcf_gz": b_tcf_gz,
            "vs_lit_pct": v_lit,
            "vs_lit_gz_pct": v_lit_gz,
            "roundtrip": rt,
        })

    # Sintese
    print("\n" + "=" * 96)
    print("Sintese — escala")
    print("=" * 96)
    print(f"\n  {'cenario':<22} {'N':>5} {'lit':>7} {'TCF':>7} "
          f"{'vs lit':>8} {'lit+gz':>7} {'TCF+gz':>7} {'vs +gz':>8} {'rt':>4}")
    print(f"  {'-'*22} {'-'*5} {'-'*7} {'-'*7} {'-'*8} {'-'*7} {'-'*7} {'-'*8} {'-'*4}")
    for r in all_results:
        rt = "OK" if r["roundtrip"] else "FAIL"
        print(f"  {r['name']:<22} {r['n']:>5} {r['literal']:>7} {r['tcf']:>7} "
              f"{r['vs_lit_pct']:>+7.1f}% {r['literal_gz']:>7} {r['tcf_gz']:>7} "
              f"{r['vs_lit_gz_pct']:>+7.1f}% {rt:>4}")

    avg_lit = sum(r["vs_lit_pct"] for r in all_results) / len(all_results)
    avg_gz = sum(r["vs_lit_gz_pct"] for r in all_results) / len(all_results)
    print(f"\n  Avg TCF vs literal:     {avg_lit:+.2f}%")
    print(f"  Avg TCF+gz vs literal+gz: {avg_gz:+.2f}%")

    # Curva por escala
    print(f"\n  Curva escala — TCF vs literal por N:")
    for r in all_results:
        bar_len = int(abs(r["vs_lit_pct"]) / 100 * 50)
        sign = "-" if r["vs_lit_pct"] < 0 else "+"
        print(f"    N={r['n']:>5}  {sign}{abs(r['vs_lit_pct']):>5.1f}%  {sign * bar_len}")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
