"""Lab 19: PATRICIA bidir + heuristica refinada + dedução de marcadores.

Pass A — heuristica gain (count * len) em vez de so len
Pass B — PATRICIA bidir (forward + reverse)
Pass C — deducao: omitir `=` quando dataset NAO tem string-idx refs

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
# PATRICIA simplificado
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
    """Retorna [(prefix, count, gain)] ordenado por gain desc."""
    out = []
    def dfs(n, acc=""):
        full = acc + n.label
        if full and len(full) >= min_len:
            ct = count_terminals(n)
            if ct >= min_count:
                # gain = count * (len - 1) - (len + 2)
                gain = ct * (len(full) - 1) - (len(full) + 2)
                if gain > 0:
                    out.append((full, ct, gain))
        for ch in n.children:
            dfs(ch, full)
    dfs(root)
    out.sort(key=lambda x: -x[2])
    return out


# ---------------------------------------------------------------------------
# Encoder com Pass A + B
# ---------------------------------------------------------------------------

def encode_bidir(values, with_deducao=False):
    if not values:
        return ""

    # Pass B: PATRICIA forward
    fwd = PatNode()
    for i, v in enumerate(values, 1):
        insert(fwd, v, i)
    prefix_cands = collect_with_gain(fwd)

    # Pass B: PATRICIA reverse (sufixos)
    rev_root = PatNode()
    for i, v in enumerate(values, 1):
        insert(rev_root, v[::-1], i)
    suffix_cands_rev = collect_with_gain(rev_root)
    suffix_cands = [(s[::-1], c, g) for s, c, g in suffix_cands_rev]

    # Pass 3: decompoe cada string
    decompositions = []
    for v in values:
        # Melhor prefix por gain (que case com v)
        best_p = ""
        best_p_gain = 0
        for p, _, gain in prefix_cands:
            if v.startswith(p) and gain > best_p_gain:
                best_p = p
                best_p_gain = gain
        rest = v[len(best_p):] if best_p else v

        # Melhor suffix por gain
        best_s = ""
        best_s_gain = 0
        for s, _, gain in suffix_cands:
            if rest.endswith(s) and gain > best_s_gain:
                best_s = s
                best_s_gain = gain
        mid = rest[:-len(best_s)] if best_s else rest
        decompositions.append((best_p, mid, best_s))

    # Pass C — deducao: vale omitir `=` ?
    # So vale se NAO ha string-idx refs (ou seja, se NENHUMA string foi
    # decomposta em prefix-mid-suffix com idx)
    has_string_idx = any(p or s for p, _, s in decompositions
                          if p or s)
    omit_eq = with_deducao and not has_string_idx

    # Pass 4: emit inline
    out = []
    declared: dict[str, int] = {}
    line_history: dict[str, int] = {}

    for line_no, (v, (best_p, mid, best_s)) in enumerate(zip(values, decompositions), 1):
        if v in line_history:
            ref = line_history[v]
            if omit_eq:
                out.append(str(ref))  # so numero
            else:
                out.append(f"={ref}")
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
            if v.isdigit():
                tokens.append(f"_{v}")
            else:
                tokens.append(v)
        out.append(" ".join(tokens))

    # Header com flag de deducao se aplicavel
    if omit_eq:
        out = ["#mode:lineRle"] + out

    return "\n".join(out) + "\n"


def decode_bidir(text):
    lines = text.splitlines()
    if not lines:
        return []

    # Detect mode
    mode = "default"
    body_start = 0
    if lines[0].startswith("#mode:lineRle"):
        mode = "lineRle"
        body_start = 1

    string_dict: list[str] = []
    line_history: list[str] = []
    out = []

    for line in lines[body_start:]:
        if not line:
            continue

        if line.startswith("="):
            ref = int(line[1:])
            v = line_history[ref - 1]
        elif mode == "lineRle" and line.isdigit() and not line.startswith("_"):
            # Modo lineRle: numero solo = ref linha
            v = line_history[int(line) - 1]
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
# Cenarios (mesmos do lab 18)
# ---------------------------------------------------------------------------

def C1_user_example():
    return [
        "user001@gmail.com", "user002@gmail.com",
        "user001@gmail.com", "user002@gmail.com",
        "user004@hotmail.com", "user006@gmail.com",
        "hdssserr@hotmail.com", "xcfdf@zipmail.com",
    ]


def C2_codigos_uniforme():
    return [f"INV-2026-{i:04d}" for i in range(1, 21)]


def C3_misto_80_20():
    out = [f"INV-2026-{i:04d}" for i in range(16)]
    out.extend([f"OUTRO_{i}" for i in range(4)])
    random.seed(42)
    random.shuffle(out)
    return out


def C4_emails_2dom():
    out = []
    for i in range(15):
        out.append(f"user{i:03d}@gmail.com")
    for i in range(15):
        out.append(f"user{i+15:03d}@yahoo.com")
    random.seed(42)
    random.shuffle(out)
    return out


def C5_dups_dominantes():
    base = ["foo", "bar", "baz"]
    random.seed(42)
    return [random.choice(base) for _ in range(15)]


def C6_4_emails():
    return [
        "user019@yahoo.com", "user014@gmail.com",
        "user010@gmail.com", "user026@yahoo.com",
    ]


SCENARIOS = [
    ("C1-user-example", C1_user_example()),
    ("C2-codigos-uniforme", C2_codigos_uniforme()),
    ("C3-misto-80-20", C3_misto_80_20()),
    ("C4-emails-2dom", C4_emails_2dom()),
    ("C5-dups-dominantes", C5_dups_dominantes()),
    ("C6-4-emails", C6_4_emails()),
]

# Bytes do lab 18 (referencia para comparativo)
LAB18 = {
    "C1-user-example": 117,
    "C2-codigos-uniforme": 136,
    "C3-misto-80-20": 130,
    "C4-emails-2dom": 304,
    "C5-dups-dominantes": 48,
    "C6-4-emails": 60,
}


def main():
    print("=" * 92)
    print("Lab 19: PATRICIA bidir + heuristica refinada + dedução")
    print("=" * 92)

    all_results = []
    for name, values in SCENARIOS:
        print("\n" + "=" * 92)
        print(f"[{name}] {len(values)} valores")
        print("=" * 92)

        scen = OUT / name
        scen.mkdir(exist_ok=True)

        literal = "\n".join(values) + "\n"
        b_lit = len(literal.encode("utf-8"))
        b_lit_gz = len(gz(literal))
        (scen / "literal.txt").write_text(literal, encoding="utf-8")

        # bidir + refined
        text_a = encode_bidir(values, with_deducao=False)
        b_a = len(text_a.encode("utf-8"))
        b_a_gz = len(gz(text_a))
        (scen / "bidir.txt").write_text(text_a, encoding="utf-8")
        try:
            decoded_a = decode_bidir(text_a)
            rt_a = decoded_a == values
        except Exception as e:
            rt_a = False

        # bidir + deducao
        text_b = encode_bidir(values, with_deducao=True)
        b_b = len(text_b.encode("utf-8"))
        b_b_gz = len(gz(text_b))
        (scen / "bidir-deducao.txt").write_text(text_b, encoding="utf-8")
        try:
            decoded_b = decode_bidir(text_b)
            rt_b = decoded_b == values
        except Exception as e:
            rt_b = False

        b18 = LAB18.get(name, None)

        print(f"\n  literal:        {b_lit}B  +gz: {b_lit_gz}")
        print(f"  lab18 (ref):    {b18}B" if b18 else "  lab18: n/a")
        print(f"  lab19 bidir:    {b_a}B  +gz: {b_a_gz}  "
              f"(vs lit: {(b_a/b_lit-1)*100:+.1f}%, "
              f"vs lab18: {(b_a/b18-1)*100:+.1f}%, rt: {'OK' if rt_a else 'FAIL'})" if b18 else "")
        print(f"  lab19 +deducao: {b_b}B  +gz: {b_b_gz}  "
              f"(vs lit: {(b_b/b_lit-1)*100:+.1f}%, rt: {'OK' if rt_b else 'FAIL'})")

        # Mostra bidir
        print(f"\n  --- bidir output (primeiras 10 linhas) ---")
        for line in text_a.splitlines()[:10]:
            print(f"    {line}")
        if len(text_a.splitlines()) > 10:
            print(f"    ... ({len(text_a.splitlines())-10} a mais)")

        all_results.append({
            "name": name, "n": len(values),
            "literal": b_lit, "lab18": b18,
            "bidir": b_a, "bidir_gz": b_a_gz, "rt_bidir": rt_a,
            "deducao": b_b, "deducao_gz": b_b_gz, "rt_deducao": rt_b,
            "bidir_vs_lab18_pct": (b_a/b18-1)*100 if b18 else None,
            "bidir_vs_lit_pct": (b_a/b_lit-1)*100,
            "deducao_vs_lit_pct": (b_b/b_lit-1)*100,
        })

    # Sintese
    print("\n" + "=" * 92)
    print("Sintese — comparativo cumulativo")
    print("=" * 92)
    print(f"\n  {'cenario':<22} {'lit':>5} {'lab18':>6} {'bidir':>6} {'+ded':>6} "
          f"{'bidir vs lab18':>15} {'bidir vs lit':>13} {'rt':>4}")
    print(f"  {'-'*22} {'-'*5} {'-'*6} {'-'*6} {'-'*6} {'-'*15} {'-'*13} {'-'*4}")
    for r in all_results:
        b18 = f"{r['lab18']}" if r['lab18'] else "-"
        v18 = f"{r['bidir_vs_lab18_pct']:+.1f}%" if r['bidir_vs_lab18_pct'] is not None else "n/a"
        v_lit = f"{r['bidir_vs_lit_pct']:+.1f}%"
        rt = "OK" if r['rt_bidir'] and r['rt_deducao'] else "FAIL"
        print(f"  {r['name']:<22} {r['literal']:>5} {b18:>6} "
              f"{r['bidir']:>6} {r['deducao']:>6} "
              f"{v18:>15} {v_lit:>13} {rt:>4}")

    avg_v_lit = sum(r["bidir_vs_lit_pct"] for r in all_results) / len(all_results)
    avg_v_lab18 = sum(r["bidir_vs_lab18_pct"] for r in all_results
                      if r["bidir_vs_lab18_pct"] is not None) / len(all_results)
    avg_dedu = sum(r["deducao_vs_lit_pct"] for r in all_results) / len(all_results)
    print(f"\n  Avg bidir vs literal: {avg_v_lit:+.2f}%")
    print(f"  Avg bidir vs lab18:   {avg_v_lab18:+.2f}%")
    print(f"  Avg +deducao vs lit:  {avg_dedu:+.2f}%")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
