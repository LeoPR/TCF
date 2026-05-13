"""Lab 21: heuristica multi-afixo com encadeamento real.

Lab 20 implementou a sintaxe `*N=P+ext` mas heuristica nao acionou
em datasets sem hierarquia profunda.

Este lab refinada a heuristica:
  - Para cada string, identifica TODOS os nos uteis no caminho da raiz
  - Decompoe em sequencia de idx (encadeada)
  - Cada idx no caminho vira decl encadeada (filho usa pai)

Sintaxe (estendida):
  *<N>=<text>           decl absoluta (raiz)
  *<N>=<P>+<ext>        decl encadeada (extensao do idx P)
  <N1>.<N2> ... mid     caminho hierarquico (raro)
  <idx>                 ref simples
  =<n>                  ref linha
  _<text>               literal (desambig)
  <text>                literal puro

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
# PATRICIA com tracking de pais
# ---------------------------------------------------------------------------

class PatNode:
    __slots__ = ("label", "children", "terminal_lines", "parent", "_full_path")
    def __init__(self, label="", parent=None):
        self.label = label
        self.children: list[PatNode] = []
        self.terminal_lines: list[int] = []
        self.parent: PatNode | None = parent
        self._full_path = None


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
            new_node = PatNode(value, parent=node)
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

        # Cria intermediario com `common`
        intermediate = PatNode(common, parent=node)

        # Antigo match perde o common e vira filho de intermediate
        match.label = old_rest
        match.parent = intermediate
        intermediate.children.append(match)

        if new_rest:
            new_n = PatNode(new_rest, parent=intermediate)
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
    """Retorna [(node, full_path, count, gain)]."""
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


# ---------------------------------------------------------------------------
# Encoder com seleção MULTI-AFIXO
# ---------------------------------------------------------------------------

def find_node_for_string(root, value):
    """Walk pela trie e retorna a sequencia de NOS no caminho que cobrem
    a string (cada no = um pedaco do prefix)."""
    nodes_in_path = []
    node = root
    consumed = 0
    while consumed < len(value):
        match = None
        for c in node.children:
            if c.label and c.label[0] == value[consumed]:
                match = c
                break
        if match is None:
            break
        # Ve quanto do label do match casa com value[consumed:]
        l = lcp_str(match.label, value[consumed:])
        if l == len(match.label):
            # Casa label inteiro
            consumed += l
            nodes_in_path.append(match)
            node = match
        else:
            # Casa parcialmente (ate o middle do label)
            break
    return nodes_in_path, consumed


def encode_multi(values):
    if not values:
        return ""

    # Pass 1: PATRICIA forward
    fwd = PatNode()
    for i, v in enumerate(values, 1):
        insert(fwd, v, i)
    useful_fwd = collect_useful(fwd)
    useful_fwd_ids = {id(n) for n, _, _, _ in useful_fwd}

    # Pass 2: PATRICIA reverse (sufixos)
    rev_root = PatNode()
    for i, v in enumerate(values, 1):
        insert(rev_root, v[::-1], i)
    useful_rev = collect_useful(rev_root)
    useful_rev_ids = {id(n) for n, _, _, _ in useful_rev}

    # Pass 3: para cada string, identifica caminho na arvore forward
    decompositions = []
    for v in values:
        # Caminho de nos no forward
        nodes_fwd, consumed_p = find_node_for_string(fwd, v)
        # So mantem nos uteis
        useful_path_fwd = [n for n in nodes_fwd if id(n) in useful_fwd_ids]

        # Resto da string para suffix matching
        rest = v[consumed_p:] if useful_path_fwd else v
        # Caminho na arvore reverse (busca pela rest invertida)
        nodes_rev, consumed_s = find_node_for_string(rev_root, rest[::-1])
        useful_path_rev = [n for n in nodes_rev if id(n) in useful_rev_ids]

        # Reconstroi prefix completo do path forward
        prefix_full = useful_path_fwd[-1]._full_path if useful_path_fwd else ""

        # Reconstroi suffix completo do path reverse (path eh sobre rev string)
        suffix_full_rev = useful_path_rev[-1]._full_path if useful_path_rev else ""
        suffix_full = suffix_full_rev[::-1]

        # Garante que prefix + (mid) + suffix = v
        if prefix_full and suffix_full and v.startswith(prefix_full) and v.endswith(suffix_full):
            mid = v[len(prefix_full):-len(suffix_full)] if suffix_full else v[len(prefix_full):]
        elif prefix_full and v.startswith(prefix_full):
            mid = v[len(prefix_full):]
            suffix_full = ""
        elif suffix_full and v.endswith(suffix_full):
            mid = v[:-len(suffix_full)]
            prefix_full = ""
        else:
            mid = v
            prefix_full = ""
            suffix_full = ""

        decompositions.append((useful_path_fwd, prefix_full, mid, suffix_full))

    # Pass 4: numerar idx por ordem de PRIMEIRO USO
    declared: dict[str, int] = {}     # full_path -> idx
    declared_paths_order = []          # lista para ordem
    line_history: dict[str, int] = {}

    out = []
    for line_no, (v, (path_fwd, p_full, mid, s_full)) in enumerate(zip(values, decompositions), 1):
        if v in line_history:
            out.append(f"={line_history[v]}")
            continue
        line_history[v] = line_no

        tokens = []

        # PREFIX — pode ser encadeado se houver path
        if p_full:
            if p_full in declared:
                tokens.append(str(declared[p_full]))
            else:
                # Determina se tem ancestral util ja declarado
                # Procura ancestral (subpath) declarado
                ancestor_path = None
                ancestor_idx = None
                for existing in declared_paths_order:
                    if existing != p_full and p_full.startswith(existing):
                        if ancestor_path is None or len(existing) > len(ancestor_path):
                            ancestor_path = existing
                            ancestor_idx = declared[existing]

                new_idx = len(declared) + 1
                declared[p_full] = new_idx
                declared_paths_order.append(p_full)

                if ancestor_path:
                    ext = p_full[len(ancestor_path):]
                    tokens.append(f"*{ancestor_idx}+{ext}")
                else:
                    # Decide se vale declarar com encadeamento futuro:
                    # se o caminho fwd tem >= 2 nos uteis na trie, pode pre-declarar
                    # ancestrais. Aqui simplificamos: declara absoluto.
                    tokens.append(f"*{p_full}")

        # MID
        if mid:
            if mid.isdigit():
                tokens.append(f"_{mid}")
            else:
                tokens.append(mid)

        # SUFFIX — encadeado tambem
        if s_full:
            if s_full in declared:
                tokens.append(str(declared[s_full]))
            else:
                # Suffixes: similar logic. Procura sufixo ja declarado tal que
                # o ja-declarado seja sufixo do nosso (s_full ends with declared).
                # Mas suffixes nao encadeiam naturalmente como prefixes.
                # Por enquanto: declara absoluto.
                new_idx = len(declared) + 1
                declared[s_full] = new_idx
                declared_paths_order.append(s_full)
                tokens.append(f"*{s_full}")

        if not tokens:
            if v.isdigit():
                tokens.append(f"_{v}")
            else:
                tokens.append(v)
        out.append(" ".join(tokens))

    return "\n".join(out) + "\n"


# Pre-declaração de ancestrais úteis
def encode_multi_with_predeclare(values):
    """Variante que PRE-DECLARA ancestrais uteis antes de descer."""
    if not values:
        return ""

    fwd = PatNode()
    for i, v in enumerate(values, 1):
        insert(fwd, v, i)
    useful_fwd = collect_useful(fwd)
    useful_fwd_ids = {id(n) for n, _, _, _ in useful_fwd}

    rev_root = PatNode()
    for i, v in enumerate(values, 1):
        insert(rev_root, v[::-1], i)
    useful_rev = collect_useful(rev_root)
    useful_rev_ids = {id(n) for n, _, _, _ in useful_rev}

    # Para cada string, identifica caminho COMPLETO de nos uteis
    paths_per_string = []
    for v in values:
        nodes_fwd, consumed_p = find_node_for_string(fwd, v)
        useful_chain = [n for n in nodes_fwd if id(n) in useful_fwd_ids]

        rest = v[consumed_p:] if nodes_fwd else v
        nodes_rev, _ = find_node_for_string(rev_root, rest[::-1])
        useful_rev_chain = [n for n in nodes_rev if id(n) in useful_rev_ids]
        # Pega o mais profundo do reverse
        suffix_node = useful_rev_chain[-1] if useful_rev_chain else None

        paths_per_string.append((useful_chain, suffix_node))

    # Identifica TODOS os nos uteis que aparecem em algum caminho
    used_fwd_ids = set()
    used_rev_ids = set()
    for chain, suf in paths_per_string:
        for n in chain:
            used_fwd_ids.add(id(n))
        if suf:
            used_rev_ids.add(id(suf))

    # Numera idx em ordem topologica (raiz primeiro)
    # Para forward: ordena por depth (rasos primeiro)
    used_fwd_nodes = [n for n, _, _, _ in useful_fwd if id(n) in used_fwd_ids]
    used_fwd_nodes.sort(key=lambda n: len(n._full_path))

    used_rev_nodes = [n for n, _, _, _ in useful_rev if id(n) in used_rev_ids]
    used_rev_nodes.sort(key=lambda n: len(n._full_path))

    # Atribui idx
    fwd_idx_map = {id(n): i + 1 for i, n in enumerate(used_fwd_nodes)}
    rev_idx_map = {id(n): len(used_fwd_nodes) + i + 1 for i, n in enumerate(used_rev_nodes)}

    # Emit
    out = []
    declared_set = set()
    line_history: dict[str, int] = {}

    # 1) Header inline: declara cada idx em ordem
    # Usa encadeamento quando aplicavel
    for i, n in enumerate(used_fwd_nodes):
        idx = fwd_idx_map[id(n)]
        full = n._full_path
        # Procura ancestral
        ancestor_idx = None
        ancestor_path = None
        for ancestor in used_fwd_nodes[:i]:
            ap = ancestor._full_path
            if ap != full and full.startswith(ap):
                if ancestor_path is None or len(ap) > len(ancestor_path):
                    ancestor_path = ap
                    ancestor_idx = fwd_idx_map[id(ancestor)]
        if ancestor_idx:
            ext = full[len(ancestor_path):]
            out.append(f"*{idx}={ancestor_idx}+{ext}")
        else:
            out.append(f"*{idx}={full}")
        declared_set.add(idx)

    for i, n in enumerate(used_rev_nodes):
        idx = rev_idx_map[id(n)]
        full_rev = n._full_path
        suffix = full_rev[::-1]
        out.append(f"*{idx}={suffix}")
        declared_set.add(idx)

    # 2) Body: cada linha emite caminho + mid
    for line_no, (v, (chain, suf_node)) in enumerate(zip(values, paths_per_string), 1):
        if v in line_history:
            out.append(f"={line_history[v]}")
            continue
        line_history[v] = line_no

        # Determina prefix mais profundo no caminho
        prefix_full = chain[-1]._full_path if chain else ""
        suffix_full = suf_node._full_path[::-1] if suf_node else ""

        # Garante consistencia
        if prefix_full and not v.startswith(prefix_full):
            prefix_full = ""
        if suffix_full and not v.endswith(suffix_full):
            suffix_full = ""
        # Verifica overlap
        if prefix_full and suffix_full and len(prefix_full) + len(suffix_full) > len(v):
            suffix_full = ""

        mid = v
        if prefix_full:
            mid = mid[len(prefix_full):]
        if suffix_full:
            mid = mid[:-len(suffix_full)] if len(mid) >= len(suffix_full) else mid

        tokens = []
        if prefix_full:
            tokens.append(str(fwd_idx_map[id(chain[-1])]))
        if mid:
            if mid.isdigit():
                tokens.append(f"_{mid}")
            else:
                tokens.append(mid)
        if suffix_full:
            tokens.append(str(rev_idx_map[id(suf_node)]))
        if not tokens:
            if v.isdigit():
                tokens.append(f"_{v}")
            else:
                tokens.append(v)
        out.append(" ".join(tokens))

    return "\n".join(out) + "\n"


def decode_multi(text):
    lines = text.splitlines()
    string_dict: dict[int, str] = {}
    line_history: list[str] = []
    out = []

    for line in lines:
        if not line:
            continue
        if line.startswith("*") and "=" in line and not line.startswith("=") and " " not in line.split("=")[0]:
            # decl: *<idx>=<rhs>  (mas pode ter espaco depois do =)
            eq = line.index("=")
            idx_str = line[1:eq]
            rhs = line[eq+1:]
            if idx_str.isdigit():
                idx = int(idx_str)
                # rhs pode ser absoluto ou encadeado
                if "+" in rhs:
                    plus = rhs.index("+")
                    parent_str = rhs[:plus]
                    if parent_str.isdigit():
                        parent_idx = int(parent_str)
                        ext = rhs[plus+1:]
                        string_dict[idx] = string_dict[parent_idx] + ext
                        continue
                string_dict[idx] = rhs
                continue

        # Linhas de body
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
# Cenarios (mesmos do lab 20 + um com hierarquia profunda)
# ---------------------------------------------------------------------------

def C1_user_example():
    return [
        "user001@gmail.com", "user002@gmail.com",
        "user001@gmail.com", "user002@gmail.com",
        "user004@hotmail.com", "user006@gmail.com",
        "hdssserr@hotmail.com", "xcfdf@zipmail.com",
    ]


def C7_urls_subpath():
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
    out = []
    for org in ["ACME", "TECH"]:
        for dept in ["FIN", "OPS", "ENG"]:
            for i in range(4):
                out.append(f"{org}-{dept}-USER-{i:03d}")
    return out


def C9_urls_4_niveis():
    """4 niveis hierarquicos."""
    out = []
    for service in ["api", "auth"]:
        for version in ["v1", "v2"]:
            for resource in ["users", "orders"]:
                for i in range(3):
                    out.append(f"https://{service}.example.com/{version}/{resource}/{i:03d}")
    return out


SCENARIOS = [
    ("C1-user-example", C1_user_example()),
    ("C7-urls-subpath", C7_urls_subpath()),
    ("C8-codigos-org-dept", C8_codigos_org_dept()),
    ("C9-urls-4-niveis", C9_urls_4_niveis()),
]

LAB20 = {
    "C1-user-example": 81,
    "C7-urls-subpath": 268,
    "C8-codigos-org-dept": 216,
    "C9-urls-4-niveis": None,
}


def main():
    print("=" * 92)
    print("Lab 21: heuristica multi-afixo + encadeamento real")
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

        text_multi = encode_multi_with_predeclare(values)
        b_multi = len(text_multi.encode("utf-8"))
        b_multi_gz = len(gz(text_multi))
        (scen / "multi.txt").write_text(text_multi, encoding="utf-8")

        try:
            decoded = decode_multi(text_multi)
            rt = decoded == values
            err = None
        except Exception as e:
            rt = False
            err = f"{type(e).__name__}: {e}"

        b20 = LAB20.get(name)
        sign = "+" if (b_multi/b_lit-1)*100 >= 0 else ""
        if b20:
            print(f"\n  literal: {b_lit}B   lab20: {b20}B   "
                  f"multi: {b_multi}B   "
                  f"(vs lab20: {(b_multi/b20-1)*100:+.1f}%, "
                  f"vs lit: {sign}{(b_multi/b_lit-1)*100:+.1f}%)")
        else:
            print(f"\n  literal: {b_lit}B   multi: {b_multi}B   "
                  f"(vs lit: {sign}{(b_multi/b_lit-1)*100:+.1f}%)")
        print(f"  rt: {'OK' if rt else 'FAIL'}{' — '+err if err else ''}")

        print(f"\n  --- multi output ---")
        for line in text_multi.splitlines()[:25]:
            print(f"    {line}")
        if len(text_multi.splitlines()) > 25:
            print(f"    ... ({len(text_multi.splitlines())-25} a mais)")

        all_results.append({
            "name": name, "n": len(values),
            "literal": b_lit, "lab20": b20,
            "multi": b_multi, "multi_gz": b_multi_gz,
            "vs_lit_pct": (b_multi/b_lit-1)*100,
            "vs_lab20_pct": (b_multi/b20-1)*100 if b20 else None,
            "roundtrip": rt,
        })

    # Sintese
    print("\n" + "=" * 92)
    print("Sintese")
    print("=" * 92)
    for r in all_results:
        rt = "OK" if r['roundtrip'] else "FAIL"
        v20 = f"{r['vs_lab20_pct']:+.1f}%" if r['vs_lab20_pct'] is not None else "n/a"
        print(f"  {r['name']:<22} lit={r['literal']:>4} lab20={str(r['lab20']):>4} "
              f"multi={r['multi']:>4} (vs20={v20:>7}, vs_lit={r['vs_lit_pct']:+.1f}%) {rt}")

    avg = sum(r["vs_lit_pct"] for r in all_results) / len(all_results)
    print(f"\n  Avg multi vs literal: {avg:+.2f}%")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")


if __name__ == "__main__":
    main()
