"""Lab 20: hierarquia profunda via encadeamento na arvore PATRICIA.

Continua lab 19 com:
  - Encadeamento de decls (*N=P+ext) usando relacao pai-filho da arvore
  - Cenarios novos com hierarquia (URLs com subpath, codigos org-dept-id)

Saida: ./output/
"""
from __future__ import annotations
import gzip
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parents[0]
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)


def gz(text):
    return gzip.compress(text.encode("utf-8"), compresslevel=9)


# ---------------------------------------------------------------------------
# PATRICIA (mesmo do lab 19)
# ---------------------------------------------------------------------------

class PatNode:
    __slots__ = ("label", "children", "terminal_lines", "_full_path")
    def __init__(self, label=""):
        self.label = label
        self.children: list[PatNode] = []
        self.terminal_lines: list[int] = []
        self._full_path = None  # cache


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


def collect_useful_nodes(root, min_count=2, min_len=4):
    """Retorna lista de (node, full_path, count, gain)."""
    out = []
    def dfs(n, acc=""):
        full = acc + n.label
        n._full_path = full
        if full and len(full) >= min_len:
            ct = count_terminals(n)
            if ct >= min_count:
                gain = ct * (len(full) - 1) - (len(full) + 2)
                if gain > 0:
                    out.append((n, full, ct, gain))
        for ch in n.children:
            dfs(ch, full)
    dfs(root)
    return out


def find_node_parent_in_useful(node, useful_set, root):
    """Acha ancestral mais proximo que tambem esta em useful_set.

    useful_set: set de id(node).
    Retorna o ancestral ou None se nenhum.
    """
    # Para isso preciso saber os pais — vou reconstruir relacao
    # via path lookup. Hack: comparar full_path prefixes.
    target = node._full_path
    candidates = []
    for n_id, n_path in useful_set.items():
        if n_path != target and target.startswith(n_path):
            candidates.append((n_id, n_path))
    if not candidates:
        return None
    # Pega o mais profundo (maior path)
    candidates.sort(key=lambda x: -len(x[1]))
    return candidates[0]


# ---------------------------------------------------------------------------
# Encoder com encadeamento
# ---------------------------------------------------------------------------

def encode_chain(values):
    if not values:
        return ""

    # Pass 1: PATRICIA forward
    fwd = PatNode()
    for i, v in enumerate(values, 1):
        insert(fwd, v, i)
    prefix_useful = collect_useful_nodes(fwd)
    prefix_useful.sort(key=lambda x: -x[3])  # gain desc

    # Pass 2: PATRICIA reverse
    rev_root = PatNode()
    for i, v in enumerate(values, 1):
        insert(rev_root, v[::-1], i)
    suffix_useful_rev = collect_useful_nodes(rev_root)
    suffix_useful_rev.sort(key=lambda x: -x[3])

    suffix_useful = [(n, p[::-1], c, g) for n, p, c, g in suffix_useful_rev]

    # Pass 3: para cada string, decompoe (best gain prefix + suffix)
    decompositions = []
    for v in values:
        best_p = ""
        best_p_gain = 0
        for n, p, c, gain in prefix_useful:
            if v.startswith(p) and gain > best_p_gain:
                best_p = p
                best_p_gain = gain
        rest = v[len(best_p):] if best_p else v

        best_s = ""
        best_s_gain = 0
        for n, s, c, gain in suffix_useful:
            if rest.endswith(s) and gain > best_s_gain:
                best_s = s
                best_s_gain = gain
        mid = rest[:-len(best_s)] if best_s else rest
        decompositions.append((best_p, mid, best_s))

    # Pass 4: filtrar so afixos USADOS
    used_prefixes = {d[0] for d in decompositions if d[0]}
    used_suffixes = {d[2] for d in decompositions if d[2]}

    # Pass 5: numerar idx (string-dict unico para prefix e suffix)
    # Ordem: pelo primeiro uso
    declared: dict[str, int] = {}
    line_history: dict[str, int] = {}

    # Pass 6: emit, com encadeamento de prefixes que sao subset de outros
    out = []

    # Constroi mapa de "qual prefix encadeia em qual"
    # Para simplificar: prefix1 encadeia com prefix2 se prefix2 eh prefix de prefix1
    # E prefix2 ja foi declarado
    def find_chain_parent(text, declared):
        """Acha o maior prefixo de `text` que esta em declared."""
        best = None
        best_len = 0
        for d_text, d_idx in declared.items():
            if d_text != text and text.startswith(d_text) and len(d_text) > best_len:
                best = (d_text, d_idx)
                best_len = len(d_text)
        return best

    for line_no, (v, (best_p, mid, best_s)) in enumerate(zip(values, decompositions), 1):
        if v in line_history:
            out.append(f"={line_history[v]}")
            continue
        line_history[v] = line_no

        tokens = []
        # Prefix
        if best_p:
            if best_p in declared:
                tokens.append(str(declared[best_p]))
            else:
                # Decide se encadeia
                chain_parent = find_chain_parent(best_p, declared)
                new_idx = len(declared) + 1
                declared[best_p] = new_idx
                if chain_parent:
                    parent_text, parent_idx = chain_parent
                    ext = best_p[len(parent_text):]
                    tokens.append(f"*{parent_idx}+{ext}")
                else:
                    tokens.append(f"*{best_p}")
        # Mid
        if mid:
            if mid.isdigit():
                tokens.append(f"_{mid}")
            else:
                tokens.append(mid)
        # Suffix (suffixes nao encadeiam por enquanto — sintatica fica complexa)
        if best_s:
            if best_s in declared:
                tokens.append(str(declared[best_s]))
            else:
                new_idx = len(declared) + 1
                declared[best_s] = new_idx
                tokens.append(f"*{best_s}")
        if not tokens:
            if v.isdigit():
                tokens.append(f"_{v}")
            else:
                tokens.append(v)
        out.append(" ".join(tokens))

    return "\n".join(out) + "\n"


def decode_chain(text):
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
                    body = tok[1:]
                    # Detecta encadeamento: <parent_idx>+<ext>
                    if "+" in body:
                        plus_pos = body.index("+")
                        first = body[:plus_pos]
                        if first.isdigit():
                            parent_idx = int(first)
                            ext = body[plus_pos+1:]
                            resolved = string_dict[parent_idx - 1] + ext
                            string_dict.append(resolved)
                            parts.append(resolved)
                            continue
                    # Decl absoluta
                    string_dict.append(body)
                    parts.append(body)
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
# Cenarios (mesmos do lab 19 + cenarios novos hierarquicos)
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


def C4_emails_2dom():
    out = []
    for i in range(15):
        out.append(f"user{i:03d}@gmail.com")
    for i in range(15):
        out.append(f"user{i+15:03d}@yahoo.com")
    random.seed(42)
    random.shuffle(out)
    return out


def C7_urls_subpath():
    """URLs com subpath profundo — hierarquia natural."""
    base = "https://api.example.com"
    return [
        f"{base}/v1/users/{i:03d}" for i in range(5)
    ] + [
        f"{base}/v1/orders/{i:03d}" for i in range(5)
    ] + [
        f"{base}/v1/products/{i:03d}" for i in range(5)
    ] + [
        f"{base}/v2/users/{i:03d}" for i in range(3)
    ]


def C8_codigos_org_dept():
    """ORG-DEPT-USER-ID com hierarquia."""
    out = []
    for org in ["ACME", "TECH"]:
        for dept in ["FIN", "OPS", "ENG"]:
            for i in range(4):
                out.append(f"{org}-{dept}-USER-{i:03d}")
    return out


SCENARIOS = [
    ("C1-user-example", C1_user_example()),
    ("C2-codigos-uniforme", C2_codigos_uniforme()),
    ("C4-emails-2dom", C4_emails_2dom()),
    ("C7-urls-subpath", C7_urls_subpath()),
    ("C8-codigos-org-dept", C8_codigos_org_dept()),
]

LAB19 = {
    "C1-user-example": 81,
    "C2-codigos-uniforme": 131,
    "C4-emails-2dom": 265,
    "C7-urls-subpath": None,
    "C8-codigos-org-dept": None,
}


def main():
    print("=" * 92)
    print("Lab 20: hierarquia profunda via encadeamento")
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

        text_chain = encode_chain(values)
        b_chain = len(text_chain.encode("utf-8"))
        b_chain_gz = len(gz(text_chain))
        (scen / "chain.txt").write_text(text_chain, encoding="utf-8")

        try:
            decoded = decode_chain(text_chain)
            rt = decoded == values
            err = None
        except Exception as e:
            rt = False
            err = f"{type(e).__name__}: {e}"

        b19 = LAB19.get(name)

        sign = "+" if (b_chain/b_lit-1)*100 >= 0 else ""
        print(f"\n  literal:   {b_lit}B   +gz: {b_lit_gz}")
        if b19:
            print(f"  lab19:     {b19}B")
        print(f"  chain:     {b_chain}B   +gz: {b_chain_gz}   "
              f"(vs lit: {sign}{(b_chain/b_lit-1)*100:+.1f}%, "
              f"vs lab19: {(b_chain/b19-1)*100:+.1f}%)" if b19 else
              f"  chain:     {b_chain}B   +gz: {b_chain_gz}   "
              f"(vs lit: {sign}{(b_chain/b_lit-1)*100:+.1f}%)")
        print(f"  rt: {'OK' if rt else 'FAIL'}{' — '+err if err else ''}")

        # Mostra encoded
        print(f"\n  --- chain output ---")
        for line in text_chain.splitlines()[:20]:
            print(f"    {line}")
        if len(text_chain.splitlines()) > 20:
            print(f"    ... ({len(text_chain.splitlines())-20} a mais)")

        all_results.append({
            "name": name, "n": len(values),
            "literal": b_lit, "lab19": b19,
            "chain": b_chain, "chain_gz": b_chain_gz,
            "vs_lit_pct": (b_chain/b_lit-1)*100,
            "vs_lab19_pct": (b_chain/b19-1)*100 if b19 else None,
            "roundtrip": rt,
        })

    # Sintese
    print("\n" + "=" * 92)
    print("Sintese")
    print("=" * 92)
    print(f"\n  {'cenario':<22} {'lit':>5} {'lab19':>6} {'chain':>6} "
          f"{'vs lab19':>10} {'vs lit':>9} {'rt':>4}")
    print(f"  {'-'*22} {'-'*5} {'-'*6} {'-'*6} {'-'*10} {'-'*9} {'-'*4}")
    for r in all_results:
        b19 = f"{r['lab19']}" if r['lab19'] else "-"
        v19 = f"{r['vs_lab19_pct']:+.1f}%" if r['vs_lab19_pct'] is not None else "n/a"
        rt = "OK" if r['roundtrip'] else "FAIL"
        print(f"  {r['name']:<22} {r['literal']:>5} {b19:>6} "
              f"{r['chain']:>6} {v19:>10} {r['vs_lit_pct']:>+8.1f}% {rt:>4}")

    avg_v_lit = sum(r["vs_lit_pct"] for r in all_results) / len(all_results)
    print(f"\n  Avg chain vs literal: {avg_v_lit:+.2f}%")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
