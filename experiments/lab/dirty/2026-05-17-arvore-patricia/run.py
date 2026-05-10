"""Lab dirty: arvore PATRICIA com segmentacao incremental.

Cada linha inserida fragmenta nos existentes baseado em LCP. Resultado:
estrutura hierarquica que captura padroes compartilhados entre strings.

Visualiza arvore + emite encoded + roundtrip.

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
# PATRICIA Node
# ---------------------------------------------------------------------------

class PatNode:
    _next_id = 0

    def __init__(self, label=""):
        PatNode._next_id += 1
        self._id = PatNode._next_id
        self.label = label
        self.children: list[PatNode] = []
        self.terminal_lines: list[int] = []  # linhas que terminam aqui

    @property
    def is_leaf(self):
        return not self.children


def lcp_str(a: str, b: str) -> int:
    """Comprimento do LCP."""
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return i


def insert(root: PatNode, value: str, line_idx: int):
    """Insere `value` na trie a partir de `root`."""
    node = root
    while True:
        if not value:
            node.terminal_lines.append(line_idx)
            return

        # Procura filho com mesmo char inicial
        match_child = None
        for c in node.children:
            if c.label and c.label[0] == value[0]:
                match_child = c
                break

        if match_child is None:
            # Adiciona como novo filho
            new_node = PatNode(value)
            new_node.terminal_lines.append(line_idx)
            node.children.append(new_node)
            return

        # Calcular LCP
        lcp_len = lcp_str(match_child.label, value)

        if lcp_len == len(match_child.label):
            # value tem prefix completo do match_child.label
            node = match_child
            value = value[lcp_len:]
            continue

        # Split necessario
        common = match_child.label[:lcp_len]
        old_rest = match_child.label[lcp_len:]
        new_rest = value[lcp_len:]

        # Cria no intermediario com `common`
        intermediate = PatNode(common)
        # Antigo match_child perde `common`
        match_child.label = old_rest
        # match_child vira filho do intermediario
        intermediate.children.append(match_child)
        # Novo no com new_rest tambem vira filho do intermediario
        if new_rest:
            new_node = PatNode(new_rest)
            new_node.terminal_lines.append(line_idx)
            intermediate.children.append(new_node)
        else:
            intermediate.terminal_lines.append(line_idx)

        # Substitui match_child por intermediate em node.children
        idx = node.children.index(match_child)
        node.children[idx] = intermediate
        return


def visualize(node: PatNode, indent="", is_last=True, accumulated="") -> str:
    """ASCII tree visualization."""
    lines = []
    if node.label or node.terminal_lines:
        connector = "└── " if is_last else "├── "
        label_disp = repr(node.label) if node.label else "(empty)"
        full_path = accumulated + node.label
        terms = f" [lines={node.terminal_lines}]" if node.terminal_lines else ""
        lines.append(f"{indent}{connector}{label_disp}{terms}")
        new_indent = indent + ("    " if is_last else "│   ")
    else:
        # root
        lines.append("root")
        full_path = ""
        new_indent = ""

    for i, child in enumerate(node.children):
        is_last_child = (i == len(node.children) - 1)
        lines.append(visualize(child, new_indent, is_last_child,
                                 accumulated + node.label))
    return "\n".join(lines)


def count_terminals(node: PatNode) -> int:
    """Quantas strings passam por este no (count)."""
    c = len(node.terminal_lines)
    for child in node.children:
        c += count_terminals(child)
    return c


def collect_all_paths(node: PatNode, accumulated="") -> list[tuple]:
    """Retorna [(line_idx, full_string, path_to_terminal)]."""
    out = []
    full_path = accumulated + node.label
    for line in node.terminal_lines:
        out.append((line, full_path))
    for child in node.children:
        out.extend(collect_all_paths(child, full_path))
    return out


# ---------------------------------------------------------------------------
# Suffix-merge optimization
# ---------------------------------------------------------------------------

def collect_suffixes(values: list[str], min_len: int = 4) -> dict[str, int]:
    """Conta sufixos comuns. Retorna {suffix: count}."""
    suffix_count: dict[str, int] = {}
    rev_strings = [v[::-1] for v in values]
    # LCP entre strings revertidas = LCS de originais
    # Greedy: para cada par, computa LCP
    for i in range(len(rev_strings)):
        for j in range(i+1, len(rev_strings)):
            l = lcp_str(rev_strings[i], rev_strings[j])
            if l >= min_len:
                suf = rev_strings[i][:l][::-1]
                suffix_count[suf] = suffix_count.get(suf, 0) + 1
    return suffix_count


# ---------------------------------------------------------------------------
# Encoder + decoder simples
# ---------------------------------------------------------------------------

def encode_patricia(values: list[str]):
    """Constroi trie + suffix-merge + emit."""
    PatNode._next_id = 0
    root = PatNode()

    for i, v in enumerate(values, 1):
        insert(root, v, i)

    # Coleta paths
    paths = collect_all_paths(root)
    paths.sort(key=lambda x: x[0])  # por linha

    # Suffix detection
    suffix_count = collect_suffixes(values, min_len=4)
    # Pega o sufixo mais frequente que aparece em >= 2 strings
    best_suffixes = sorted(suffix_count.items(), key=lambda x: (-x[1], -len(x[0])))
    # Filtra: pega no maximo 3 sufixos com count >= 2
    suffix_idx: dict[str, int] = {}
    for suf, cnt in best_suffixes:
        if cnt >= 2 and len(suffix_idx) < 3:
            # Verifica que esse suffix nao eh sub-string de outro ja escolhido
            already = False
            for chosen in suffix_idx:
                if chosen.endswith(suf) or suf.endswith(chosen):
                    already = True
                    break
            if not already:
                suffix_idx[suf] = len(suffix_idx) + 1

    # Coleta nos internos com count >= 2 (candidatos a prefix-idx)
    candidate_prefixes: dict[str, int] = {}
    def collect_prefix_candidates(n, acc=""):
        full = acc + n.label
        ct = count_terminals(n)
        if ct >= 2 and len(full) >= 4:
            candidate_prefixes[full] = ct
        for ch in n.children:
            collect_prefix_candidates(ch, full)
    collect_prefix_candidates(root)

    # Pass 1 de uso: simula qual prefix cada string escolheria (mais profundo)
    used_prefixes: set[str] = set()
    for _, full in paths:
        best_p = ""
        for p in candidate_prefixes:
            if full.startswith(p) and len(p) > len(best_p):
                best_p = p
        if best_p:
            used_prefixes.add(best_p)

    # So declara os realmente usados
    final_prefixes = {p: candidate_prefixes[p] for p in used_prefixes}
    sorted_prefixes = sorted(final_prefixes.keys(), key=lambda p: -len(p))
    prefix_idx = {p: i+1 for i, p in enumerate(sorted_prefixes)}

    # Idem para suffix: filtrar so os usados
    used_suffixes: set[str] = set()
    for _, full in paths:
        best_p = ""
        for p in prefix_idx:
            if full.startswith(p) and len(p) > len(best_p):
                best_p = p
        rest = full[len(best_p):]
        best_s = ""
        for s in suffix_idx:
            if rest.endswith(s) and len(s) > len(best_s):
                best_s = s
        if best_s:
            used_suffixes.add(best_s)
    suffix_idx = {s: i+1 for i, s in enumerate(sorted(used_suffixes, key=lambda s: -len(s)))}

    # Emit
    out_lines = []

    # Header com decls
    decls = []
    for p, idx in sorted(prefix_idx.items(), key=lambda x: x[1]):
        decls.append(f"*p{idx}={p}")
    for s, idx in sorted(suffix_idx.items(), key=lambda x: x[1]):
        decls.append(f"*s{idx}={s}")
    if decls:
        out_lines.extend(decls)

    seen_lines: dict[str, int] = {}
    for line_no, full in paths:
        if full in seen_lines:
            out_lines.append(f"={seen_lines[full]}")
            continue
        seen_lines[full] = line_no

        # Encontra melhor prefix idx (maior len que casa)
        best_p = ""
        best_p_idx = None
        for p, idx in prefix_idx.items():
            if full.startswith(p) and len(p) > len(best_p):
                best_p = p
                best_p_idx = idx

        # Encontra melhor suffix idx
        rest = full[len(best_p):] if best_p else full
        best_s = ""
        best_s_idx = None
        for s, idx in suffix_idx.items():
            if rest.endswith(s) and len(s) > len(best_s):
                best_s = s
                best_s_idx = idx

        # Constroi linha
        tokens = []
        if best_p_idx is not None:
            tokens.append(f"p{best_p_idx}")
        # mid
        mid = rest[:-len(best_s)] if best_s else rest
        if mid:
            # Se mid eh puramente numero, marca com _
            if mid.isdigit():
                tokens.append(f"_{mid}")
            else:
                tokens.append(mid)
        if best_s_idx is not None:
            tokens.append(f"s{best_s_idx}")
        if not tokens:
            tokens.append(f"_{full}" if full.isdigit() else full)

        out_lines.append(" ".join(tokens))

    return "\n".join(out_lines) + "\n"


def decode_patricia(text: str) -> list[str]:
    lines = text.splitlines()
    prefix_dict: dict[str, str] = {}  # "p1" -> value
    suffix_dict: dict[str, str] = {}  # "s1" -> value
    out = []
    line_history: list[str] = []

    for line in lines:
        if not line:
            continue

        # Decl?
        if line.startswith("*p") and "=" in line:
            key, val = line[1:].split("=", 1)
            prefix_dict[key] = val
            continue
        if line.startswith("*s") and "=" in line:
            key, val = line[1:].split("=", 1)
            suffix_dict[key] = val
            continue

        if line.startswith("="):
            ref = int(line[1:])
            v = line_history[ref - 1]
        else:
            tokens = line.split(" ")
            parts = []
            for tok in tokens:
                if tok.startswith("p") and tok[1:].isdigit():
                    parts.append(prefix_dict[tok])
                elif tok.startswith("s") and tok[1:].isdigit():
                    parts.append(suffix_dict[tok])
                elif tok.startswith("_"):
                    parts.append(tok[1:])
                else:
                    parts.append(tok)
            v = "".join(parts)

        out.append(v)
        line_history.append(v)
    return out


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

def C1_user_4_emails():
    return [
        "user019@yahoo.com",
        "user014@gmail.com",
        "user010@gmail.com",
        "user026@yahoo.com",
    ]


def C2_emails_2dom():
    out = []
    for i in range(15):
        out.append(f"user{i:03d}@gmail.com")
    for i in range(15):
        out.append(f"user{i+15:03d}@yahoo.com")
    random.seed(42)
    random.shuffle(out)
    return out


def C3_codigos_uniforme():
    return [f"PED-2026-{i:04d}" for i in range(1, 21)]


def C4_user_full_example():
    return [
        "user001@gmail.com",
        "user002@gmail.com",
        "user001@gmail.com",
        "user002@gmail.com",
        "user004@hotmail.com",
        "user006@gmail.com",
        "hdssserr@hotmail.com",
        "xcfdf@zipmail.com",
    ]


SCENARIOS = [
    ("C1-user-4-emails", C1_user_4_emails()),
    ("C4-user-full",      C4_user_full_example()),
    ("C2-emails-2dom",    C2_emails_2dom()),
    ("C3-codigos-uniforme", C3_codigos_uniforme()),
]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main():
    print("=" * 90)
    print("Arvore PATRICIA com segmentacao incremental")
    print("=" * 90)

    all_results = []

    for name, values in SCENARIOS:
        print("\n" + "=" * 90)
        print(f"[{name}] {len(values)} valores")
        print("=" * 90)

        scen = OUT / name
        scen.mkdir(exist_ok=True)

        # Constroi arvore
        PatNode._next_id = 0
        root = PatNode()
        for i, v in enumerate(values, 1):
            insert(root, v, i)

        tree_viz = visualize(root)
        (scen / "tree.txt").write_text(tree_viz, encoding="utf-8")

        # Encode
        text_enc = encode_patricia(values)
        (scen / "encoded.txt").write_text(text_enc, encoding="utf-8")

        # Literal
        literal = "\n".join(values) + "\n"
        b_lit = len(literal.encode("utf-8"))
        b_enc = len(text_enc.encode("utf-8"))
        (scen / "literal.txt").write_text(literal, encoding="utf-8")

        try:
            decoded = decode_patricia(text_enc)
            rt = decoded == values
            err = None
        except Exception as e:
            rt = False
            err = f"{type(e).__name__}: {e}"

        sign = "+" if (b_enc/b_lit-1)*100 >= 0 else ""
        print(f"\n  literal: {b_lit}B   encoded: {b_enc}B   "
              f"({sign}{(b_enc/b_lit-1)*100:+.1f}%)   "
              f"rt: {'OK' if rt else 'FAIL'}")
        if err:
            print(f"  err: {err}")

        # Mostra arvore (se pequena)
        if len(values) <= 10:
            print(f"\n  --- arvore ---")
            for line in tree_viz.splitlines()[:25]:
                print(f"    {line}")

            print(f"\n  --- encoded ---")
            for line in text_enc.splitlines()[:25]:
                print(f"    {line}")
        else:
            print(f"\n  --- arvore (primeiros 20 nos) ---")
            for line in tree_viz.splitlines()[:20]:
                print(f"    {line}")
            print(f"\n  --- encoded (primeiras 12 linhas) ---")
            for line in text_enc.splitlines()[:12]:
                print(f"    {line}")

        all_results.append({
            "name": name, "n": len(values),
            "literal": b_lit, "encoded": b_enc,
            "vs_lit_pct": (b_enc/b_lit-1)*100,
            "roundtrip": rt, "err": err,
        })

    # Sintese
    print("\n" + "=" * 90)
    print("Sintese")
    print("=" * 90)
    print(f"\n  {'cenario':<22} {'lit':>5} {'enc':>5} {'vs lit':>9} {'rt':>4}")
    print(f"  {'-'*22} {'-'*5} {'-'*5} {'-'*9} {'-'*4}")
    for r in all_results:
        rt = "OK" if r["roundtrip"] else "FAIL"
        sign = "+" if r["vs_lit_pct"] >= 0 else ""
        print(f"  {r['name']:<22} {r['literal']:>5} {r['encoded']:>5} "
              f"{sign}{r['vs_lit_pct']:>+7.1f}% {rt:>4}")

    avg = sum(r["vs_lit_pct"] for r in all_results) / len(all_results)
    print(f"\n  Avg vs literal: {avg:+.2f}%")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
