"""Lab 24: fechamento — multi-afixo correto nos cenarios de escala.

Problema diagnosticado no rascunho inicial:
  1. find_node_for_string consumia ate a folha (cada string unica), entao
     o reverse trie nunca era acionado. Sufixos como `@gmail.com` perdidos.
  2. Filtro de ganho aceitava nos com count >= 2 mas custo de decl encadeada
     `*N=P+ext` excedia ganho para extensoes pequenas (ex: user004 com ct=10).

Reescrita:
  - Coleta candidatos prefix/suffix (PATRICIA) sem walk-to-leaf.
  - Para cada string: base = prefix de maior gain; ext = prefix encadeado de
    maior gain LIQUIDO (ext-aware: ct*(len_ext-1) - (5+len_ext)).
  - Suffix sobre o que sobra apos base+ext.
  - Numera idx em ordem topologica (bases por gain desc, depois exts, depois sufixos).
  - Header com encadeamento `*N=P+ext` quando aplicavel.

Compara contra lab 23 (mono-prefix gain) nos mesmos 7 cenarios.
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
# PATRICIA + collect_useful
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


def collect_useful(root, min_count=2, min_len=4):
    """Retorna [(full_path, count, gain_absoluto)] ordenado por gain DESC."""
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


# ---------------------------------------------------------------------------
# Encoder lab 24: base + ext encadeada + sufixo (ext-aware gain)
# ---------------------------------------------------------------------------

def decompose(v, prefix_cands, suffix_cands, prefix_info_by_full):
    """Decompoe v em (base, ext, mid, suffix).

    base   = prefix de maior GAIN absoluto que prefixa v
    ext    = extensao adicional de base (encadeada) com maior GAIN LIQUIDO
             positivo, considerando custo de decl `*N=P+ext` ~ 5 + len(ext)
    suffix = sufixo de maior gain do reverse que sufixa o resto
    mid    = o que sobra
    """
    # Base
    base = ""
    base_gain = 0
    for p, ct, gain in prefix_cands:
        if v.startswith(p):
            base = p
            base_gain = gain
            break  # ordenado por gain desc

    # Ext: maior net positivo
    # Formula conservadora: idx custa ~2 chars em media (>= 10 idx tipico),
    # entao economia por uso = (len_ext - 2). Decl encadeada custa
    # ~7 + len_ext (`*NN=PP+EXT\n`).
    best_ext = ""
    best_ext_net = 0
    if base:
        for p, ct, gain in prefix_cands:
            if p == base or not p.startswith(base):
                continue
            if not v.startswith(p):
                continue
            ext = p[len(base):]
            net = ct * (len(ext) - 2) - (7 + len(ext))
            if net > best_ext_net:
                best_ext_net = net
                best_ext = ext

    full_p = base + best_ext
    rest = v[len(full_p):] if full_p else v

    # Suffix
    best_s = ""
    best_s_gain = 0
    for s, ct, gain in suffix_cands:
        if rest.endswith(s) and gain > best_s_gain:
            best_s = s
            best_s_gain = gain

    mid = rest[:-len(best_s)] if best_s else rest
    return base, best_ext, mid, best_s


def encode(values):
    if not values:
        return ""

    fwd = PatNode()
    for i, v in enumerate(values, 1):
        insert(fwd, v, i)
    prefix_cands = collect_useful(fwd)
    prefix_info = {full: (ct, gain) for full, ct, gain in prefix_cands}

    rev = PatNode()
    for i, v in enumerate(values, 1):
        insert(rev, v[::-1], i)
    suffix_cands_rev = collect_useful(rev)
    suffix_cands = [(s[::-1], ct, gain) for s, ct, gain in suffix_cands_rev]
    suffix_cands.sort(key=lambda x: -x[2])

    # Decompose cada string
    decompositions = [
        decompose(v, prefix_cands, suffix_cands, prefix_info) for v in values
    ]

    # Coleta uso real
    bases_used = {b for b, _, _, _ in decompositions if b}
    full_ps_used = {(b + e) for b, e, _, _ in decompositions if b and e}
    suffixes_used = {s for _, _, _, s in decompositions if s}

    # Numera idx em ordem topologica:
    # 1) bases (por gain desc)
    # 2) full_ps (que sao base+ext) — depois das bases
    # 3) suffixes (por gain desc)
    next_idx = 1
    idx_map = {}  # full_str -> idx

    bases_ordered = sorted(bases_used, key=lambda b: -prefix_info[b][1])
    for b in bases_ordered:
        idx_map[b] = next_idx
        next_idx += 1

    fulls_ordered = sorted(full_ps_used, key=lambda f: -prefix_info[f][1])
    for f in fulls_ordered:
        if f not in idx_map:
            idx_map[f] = next_idx
            next_idx += 1

    suffix_info = {s: (ct, gain) for s, ct, gain in suffix_cands}
    suffixes_ordered = sorted(suffixes_used, key=lambda s: -suffix_info[s][1])
    for s in suffixes_ordered:
        if s not in idx_map:
            idx_map[s] = next_idx
            next_idx += 1

    out = []

    # Header — bases (absolutas), full_ps (encadeadas), sufixos (absolutos)
    for b in bases_ordered:
        out.append(f"*{idx_map[b]}={b}")
    for f in fulls_ordered:
        # f = base + ext, base ja declarado
        # Acha base
        base = ""
        for b in bases_used:
            if f.startswith(b) and len(b) > len(base):
                base = b
        ext = f[len(base):] if base else f
        if base:
            out.append(f"*{idx_map[f]}={idx_map[base]}+{ext}")
        else:
            out.append(f"*{idx_map[f]}={f}")
    for s in suffixes_ordered:
        out.append(f"*{idx_map[s]}={s}")

    # Body
    line_history: dict[str, int] = {}
    for line_no, (v, (b, e, mid, s)) in enumerate(zip(values, decompositions), 1):
        if v in line_history:
            out.append(f"={line_history[v]}")
            continue
        line_history[v] = line_no

        tokens = []
        full_p = b + e
        if full_p:
            tokens.append(str(idx_map[full_p]))
        if mid:
            if mid.isdigit():
                tokens.append(f"_{mid}")
            else:
                tokens.append(mid)
        if s:
            tokens.append(str(idx_map[s]))
        if not tokens:
            if v.isdigit():
                tokens.append(f"_{v}")
            else:
                tokens.append(v)
        out.append(" ".join(tokens))

    return "\n".join(out) + "\n"


def decode(text):
    lines = text.splitlines()
    string_dict: dict[int, str] = {}
    line_history: list[str] = []
    out = []

    for line in lines:
        if not line:
            continue

        # decl: *<idx>=<rhs>
        if line.startswith("*") and "=" in line:
            head_until_eq = line.split("=", 1)[0]
            if head_until_eq[1:].isdigit() and " " not in head_until_eq:
                eq = line.index("=")
                idx = int(line[1:eq])
                rhs = line[eq + 1:]
                if "+" in rhs:
                    plus = rhs.index("+")
                    parent_str = rhs[:plus]
                    if parent_str.isdigit():
                        parent_idx = int(parent_str)
                        ext = rhs[plus + 1:]
                        string_dict[idx] = string_dict[parent_idx] + ext
                        continue
                string_dict[idx] = rhs
                continue

        # body
        if line.startswith("="):
            ref = int(line[1:])
            v = line_history[ref - 1]
        else:
            tokens = line.split(" ")
            parts = []
            for tok in tokens:
                if tok.startswith("_"):
                    parts.append(tok[1:])
                elif tok.isdigit():
                    parts.append(string_dict[int(tok)])
                else:
                    parts.append(tok)
            v = "".join(parts)

        out.append(v)
        line_history.append(v)

    return out


# ---------------------------------------------------------------------------
# Cenarios identicos ao lab 23
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

LAB23 = {
    "E1-emails-100":      815,
    "E2-emails-1000":    9015,
    "E3-codigos-100":     622,
    "E4-codigos-1000":   7022,
    "E5-categoricas-100": 332,
    "E6-misturado-500":  3858,
    "E7-urls-1000":     14443,
}


def main():
    print("=" * 100)
    print("Lab 24: fechamento — multi-afixo nos cenarios de escala")
    print("=" * 100)

    all_results = []

    for name, values in SCENARIOS:
        print("\n" + "=" * 100)
        print(f"[{name}] {len(values)} valores")
        print("=" * 100)

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

        (scen / "tcf24.txt").write_text(
            text[:5000] + ("\n... (truncado)" if len(text) > 5000 else ""),
            encoding="utf-8",
        )

        b_lab23 = LAB23[name]
        v_lit = (b_tcf / b_lit - 1) * 100
        v_lit_gz = (b_tcf_gz / b_lit_gz - 1) * 100
        v_lab23 = (b_tcf / b_lab23 - 1) * 100

        sign = lambda x: "+" if x >= 0 else ""

        print(f"\n  N={len(values)}")
        print(f"  literal:    {b_lit:>7}B  +gz: {b_lit_gz:>5}")
        print(f"  TCF lab23:  {b_lab23:>7}B  (mono-prefixo)")
        print(f"  TCF lab24:  {b_tcf:>7}B  +gz: {b_tcf_gz:>5}  (multi-afixo gain-aditivo)")
        print(f"  vs literal:        {sign(v_lit)}{v_lit:.1f}%")
        print(f"  vs lab23:          {sign(v_lab23)}{v_lab23:.1f}%")
        print(f"  TCF+gz vs lit+gz:  {sign(v_lit_gz)}{v_lit_gz:.1f}%")
        print(f"  RT: {'OK' if rt else 'FAIL'}{' — '+err if err else ''}")

        all_results.append({
            "name": name, "n": len(values),
            "literal": b_lit, "literal_gz": b_lit_gz,
            "tcf_lab23": b_lab23,
            "tcf_lab24": b_tcf, "tcf_lab24_gz": b_tcf_gz,
            "vs_lit_pct": v_lit,
            "vs_lit_gz_pct": v_lit_gz,
            "vs_lab23_pct": v_lab23,
            "roundtrip": rt,
        })

    # Sintese
    print("\n" + "=" * 100)
    print("Sintese — fechamento")
    print("=" * 100)
    print(f"\n  {'cenario':<22} {'N':>5} {'lit':>7} {'lab23':>7} {'lab24':>7} "
          f"{'vs23':>8} {'vs lit':>8} {'+gz':>8} {'rt':>4}")
    print(f"  {'-'*22} {'-'*5} {'-'*7} {'-'*7} {'-'*7} {'-'*8} {'-'*8} {'-'*8} {'-'*4}")
    for r in all_results:
        rt = "OK" if r["roundtrip"] else "FAIL"
        print(f"  {r['name']:<22} {r['n']:>5} {r['literal']:>7} {r['tcf_lab23']:>7} "
              f"{r['tcf_lab24']:>7} {r['vs_lab23_pct']:>+7.1f}% "
              f"{r['vs_lit_pct']:>+7.1f}% {r['vs_lit_gz_pct']:>+7.1f}% {rt:>4}")

    avg_lit = sum(r["vs_lit_pct"] for r in all_results) / len(all_results)
    avg_gz = sum(r["vs_lit_gz_pct"] for r in all_results) / len(all_results)
    avg_lab23 = sum(r["vs_lab23_pct"] for r in all_results) / len(all_results)
    rt_ok = sum(1 for r in all_results if r["roundtrip"])
    print(f"\n  Avg TCF lab24 vs literal:  {avg_lit:+.2f}%")
    print(f"  Avg TCF lab24 vs lab23:    {avg_lab23:+.2f}%")
    print(f"  Avg TCF+gz vs literal+gz:  {avg_gz:+.2f}%")
    print(f"  Roundtrip: {rt_ok}/{len(all_results)}")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")


if __name__ == "__main__":
    main()
