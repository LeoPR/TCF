"""Lab dirty: PATRICIA (analise) + inline serialization (emit).

Combina:
  - Lab 17 (PATRICIA): descobre afixos globais via arvore
  - Lab 16 (inline): emit com declaracoes na 1a ocorrencia, sem header

Sintaxe (do lab 16):
  *<text>  decl inline (cria novo idx)
  <n>      ref idx (puro digito)
  _<n>     literal numerico
  =<n>     ref linha
  <text>   literal puro

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
# PATRICIA (do lab 17, simplificado)
# ---------------------------------------------------------------------------

class PatNode:
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


def collect_useful_prefixes(root, min_count=2, min_len=4):
    """DFS coletando prefixes (caminhos completos da raiz) com count >= min."""
    prefixes: list[tuple[str, int]] = []
    def dfs(n, acc=""):
        full = acc + n.label
        if full and len(full) >= min_len:
            ct = count_terminals(n)
            if ct >= min_count:
                prefixes.append((full, ct))
        for ch in n.children:
            dfs(ch, full)
    dfs(root)
    return prefixes


def collect_useful_suffixes(values, min_count=2, min_len=4):
    """LCP em strings revertidas para detectar suffixes."""
    rev = [v[::-1] for v in values]
    rev_root = PatNode()
    for i, v in enumerate(rev, 1):
        insert(rev_root, v, i)
    suf_rev = collect_useful_prefixes(rev_root, min_count, min_len)
    return [(s[::-1], c) for s, c in suf_rev]


# ---------------------------------------------------------------------------
# Encoder combinado
# ---------------------------------------------------------------------------

def encode_combined(values):
    """PATRICIA analise + inline emit."""
    if not values:
        return ""

    # Pass 1: trie e coleta de afixos
    root = PatNode()
    for i, v in enumerate(values, 1):
        insert(root, v, i)

    prefix_candidates = collect_useful_prefixes(root, min_count=2, min_len=4)
    suffix_candidates = collect_useful_suffixes(values, min_count=2, min_len=4)

    # Ordena por len desc (prefere afixos longos)
    prefix_candidates.sort(key=lambda x: (-len(x[0]), -x[1]))
    suffix_candidates.sort(key=lambda x: (-len(x[0]), -x[1]))

    prefix_set = {p for p, _ in prefix_candidates}
    suffix_set = {s for s, _ in suffix_candidates}

    # Pass 2: para cada string, decompoe usando o melhor afixo
    decompositions = []
    for v in values:
        # Melhor prefix (mais longo que casa)
        best_p = ""
        for p, _ in prefix_candidates:
            if v.startswith(p) and len(p) > len(best_p):
                best_p = p
                break  # ja ordenado por len desc
        rest = v[len(best_p):] if best_p else v
        # Melhor suffix
        best_s = ""
        for s, _ in suffix_candidates:
            if rest.endswith(s) and len(s) > len(best_s):
                best_s = s
                break
        mid = rest[:-len(best_s)] if best_s else rest
        decompositions.append((best_p, mid, best_s))

    # Pass 3: filtrar afixos REALMENTE usados
    used_prefixes = {d[0] for d in decompositions if d[0]}
    used_suffixes = {d[2] for d in decompositions if d[2]}

    # Pass 4: emit inline
    out = []
    declared: dict[str, int] = {}  # afixo -> idx (unico para todos os afixos)
    line_history: dict[str, int] = {}

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
                declared[best_p] = len(declared) + 1
                tokens.append(f"*{best_p}")
        # Mid
        if mid:
            if mid.isdigit():
                tokens.append(f"_{mid}")
            else:
                tokens.append(mid)
        # Suffix
        if best_s:
            if best_s in declared:
                tokens.append(str(declared[best_s]))
            else:
                declared[best_s] = len(declared) + 1
                tokens.append(f"*{best_s}")
        # Sem afixo nenhum (literal puro)
        if not tokens:
            tokens.append(f"_{v}" if v.isdigit() else v)
        out.append(" ".join(tokens))

    return "\n".join(out) + "\n"


def decode_combined(text):
    """Decoder unico (do lab 16)."""
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
                    text_decl = tok[1:]
                    string_dict.append(text_decl)
                    parts.append(text_decl)
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
# Cenarios (mesmos do lab 16)
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


def C6_4_emails_user():
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
    ("C6-4-emails", C6_4_emails_user()),
]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main():
    print("=" * 90)
    print("PATRICIA + inline (combinado)")
    print("=" * 90)

    all_results = []
    for name, values in SCENARIOS:
        print("\n" + "=" * 90)
        print(f"[{name}] {len(values)} valores")
        print("=" * 90)

        scen = OUT / name
        scen.mkdir(exist_ok=True)

        literal = "\n".join(values) + "\n"
        b_lit = len(literal.encode("utf-8"))
        b_lit_gz = len(gz(literal))
        (scen / "literal.txt").write_text(literal, encoding="utf-8")

        text_enc = encode_combined(values)
        b_enc = len(text_enc.encode("utf-8"))
        b_enc_gz = len(gz(text_enc))
        (scen / "encoded.txt").write_text(text_enc, encoding="utf-8")

        try:
            decoded = decode_combined(text_enc)
            rt = decoded == values
            err = None
        except Exception as e:
            rt = False
            err = f"{type(e).__name__}: {e}"

        sign = "+" if (b_enc/b_lit-1)*100 >= 0 else ""
        print(f"\n  literal: {b_lit}B   encoded: {b_enc}B   "
              f"({sign}{(b_enc/b_lit-1)*100:+.1f}%)   "
              f"+gz: {b_lit_gz} → {b_enc_gz}   "
              f"rt: {'OK' if rt else 'FAIL'}")
        if err:
            print(f"  err: {err}")

        # Mostra encoded
        print(f"\n  --- encoded ({len(text_enc.splitlines())} linhas) ---")
        for line in text_enc.splitlines()[:15]:
            print(f"    {line}")
        if len(text_enc.splitlines()) > 15:
            print(f"    ... ({len(text_enc.splitlines())-15} a mais)")

        all_results.append({
            "name": name, "n": len(values),
            "literal": b_lit, "encoded": b_enc,
            "literal_gz": b_lit_gz, "encoded_gz": b_enc_gz,
            "vs_lit_pct": (b_enc/b_lit-1)*100,
            "roundtrip": rt, "err": err,
        })

    # Sintese — comparativo com labs anteriores
    print("\n" + "=" * 90)
    print("Sintese — comparativo com labs anteriores")
    print("=" * 90)

    # Bytes do lab 16 (multi-index inline) — copiados dos resultados
    lab16 = {
        "C1-user-example": 98,
        "C2-codigos-uniforme": 211,
        "C3-misto-80-20": 256,
        "C4-emails-2dom": 399,
        "C5-dups-dominantes": 48,
        "C6-4-emails": None,  # lab 16 nao tinha
    }
    # Bytes do lab 17 (PATRICIA + header) — copiados
    lab17 = {
        "C1-user-example": None,
        "C2-codigos-uniforme": None,
        "C3-misto-80-20": None,
        "C4-emails-2dom": 462,
        "C5-dups-dominantes": None,
        "C6-4-emails": 87,
    }

    print(f"\n  {'cenario':<22} {'lit':>5} {'lab16':>6} {'lab17':>6} "
          f"{'lab18':>6} {'18 vs 16':>10} {'18 vs lit':>10} {'rt':>4}")
    print(f"  {'-'*22} {'-'*5} {'-'*6} {'-'*6} {'-'*6} {'-'*10} {'-'*10} {'-'*4}")
    for r in all_results:
        n = r["name"]
        b16 = lab16.get(n)
        b17 = lab17.get(n)
        b18 = r["encoded"]
        v16 = f"{(b18/b16-1)*100:+.1f}%" if b16 else "n/a"
        v_lit = f"{r['vs_lit_pct']:+.1f}%"
        rt = "OK" if r["roundtrip"] else "FAIL"
        print(f"  {n:<22} {r['literal']:>5} "
              f"{b16 if b16 else '-':>6} {b17 if b17 else '-':>6} {b18:>6} "
              f"{v16:>10} {v_lit:>10} {rt:>4}")

    avg_v_lit = sum(r["vs_lit_pct"] for r in all_results) / len(all_results)
    print(f"\n  Avg lab18 vs literal: {avg_v_lit:+.2f}%")

    # Bytes apos gzip
    print(f"\n  Bytes apos gzip:")
    print(f"  {'cenario':<22} {'lit+gz':>7} {'enc+gz':>7} {'vs lit':>9}")
    for r in all_results:
        diff = (r["encoded_gz"]/r["literal_gz"]-1)*100 if r["literal_gz"] else 0
        sign = "+" if diff >= 0 else ""
        print(f"  {r['name']:<22} {r['literal_gz']:>7} {r['encoded_gz']:>7} "
              f"{sign}{diff:>+7.1f}%")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
