"""Lab dirty (parte 2): trie com 3 variantes de declaracao + suffix trie.

Implementa:
  V1 — header com declaracoes ABSOLUTAS  (`*1=user0`, `*2=user02`)
  V2 — header com declaracoes ENCADEADAS (`*1=user0`, `*2=1+2`)
  V3 — declaracoes INLINE no body        (`*user0 57@gmail.com`)

Cada variante para PREFIX e SUFFIX (right-to-left).

Total: 6 codificacoes por cenario. Roundtrip em todas.

Saida: ./output-suffix/
"""
from __future__ import annotations
import csv
import gzip
import io
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from tcf.v05 import encode as tcf_encode, Flags

HERE = Path(__file__).resolve().parent
OUT = HERE / "output-suffix"
OUT.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Trie generica (funciona para prefix ou suffix via reversao)
# ---------------------------------------------------------------------------

@dataclass
class TrieNode:
    char: str = ""
    parent: "TrieNode | None" = None
    children: dict = field(default_factory=dict)
    count: int = 0

    @property
    def depth(self) -> int:
        d = 0
        n = self.parent
        while n is not None:
            d += 1
            n = n.parent
        return d

    def prefix(self) -> str:
        chars = []
        n = self
        while n.parent is not None:
            chars.append(n.char)
            n = n.parent
        return "".join(reversed(chars))


def build_trie(strings):
    root = TrieNode()
    for s in strings:
        node = root
        for c in s:
            if c not in node.children:
                node.children[c] = TrieNode(char=c, parent=node)
            node = node.children[c]
            node.count += 1
    return root


def collect_useful(root: TrieNode, min_count: int = 2,
                    min_depth: int = 4) -> list[TrieNode]:
    out = []
    def dfs(node):
        if node.parent is not None:
            if node.count >= min_count and node.depth >= min_depth:
                out.append(node)
        for c in node.children.values():
            dfs(c)
    dfs(root)
    return out


def select_deepest(strings, root, useful_set):
    out = []
    for s in strings:
        node = root
        deepest = None
        for c in s:
            if c not in node.children:
                break
            node = node.children[c]
            if id(node) in useful_set:
                deepest = node
        if deepest is None:
            out.append((None, s))
        else:
            prefix = deepest.prefix()
            out.append((deepest, s[len(prefix):]))
    return out


def optimize_trie_selection(strings: list[str]) -> tuple[list[TrieNode], list[tuple]]:
    """Constroi trie + seleciona so prefixos REALMENTE usados.

    Retorna (lista ordenada de nos uteis, decomposicoes [(node, suffix)]).
    """
    root = build_trie(strings)
    useful_pool = collect_useful(root, min_count=2, min_depth=4)
    pool_set = set(id(n) for n in useful_pool)

    # 1a passada: pega mais profundo do pool
    decomp1 = select_deepest(strings, root, pool_set)
    used1 = {id(n) for n, _ in decomp1 if n is not None}

    # 2a passada: refina com so os usados
    used_nodes = [n for n in useful_pool if id(n) in used1]
    used_set = {id(n) for n in used_nodes}
    decomp2 = select_deepest(strings, root, used_set)

    # 3a: garantir consistencia
    final_used = {id(n) for n, _ in decomp2 if n is not None}
    final_nodes = [n for n in used_nodes if id(n) in final_used]
    final_set = {id(n) for n in final_nodes}
    final_decomp = select_deepest(strings, root, final_set)

    final_nodes.sort(key=lambda n: (-n.count, -n.depth))
    return final_nodes, final_decomp


# ---------------------------------------------------------------------------
# Encoder PREFIX — 3 variantes
# ---------------------------------------------------------------------------

def encode_prefix_V1(strings, col_name="col"):
    """Header com declaracoes absolutas."""
    nodes, decomp = optimize_trie_selection(strings)
    id_to_idx = {id(n): i + 1 for i, n in enumerate(nodes)}

    out = [f"{col_name},p:"]
    for n in nodes:
        out.append(f"*{id_to_idx[id(n)]}={n.prefix()}")
    for node, suffix in decomp:
        if node is None:
            out.append(f"\\!{suffix}")
        else:
            out.append(f"{id_to_idx[id(node)]} {suffix}")
    return "\n".join(out) + "\n"


def encode_prefix_V2(strings, col_name="col"):
    """Header com declaracoes encadeadas (*idx=parent_idx ext)."""
    nodes, decomp = optimize_trie_selection(strings)
    # Ordem: shorter prefixes primeiro (so podemos ref a prefix ja declarado)
    nodes_sorted = sorted(nodes, key=lambda n: (n.depth, -n.count))
    id_to_idx = {id(n): i + 1 for i, n in enumerate(nodes_sorted)}

    out = [f"{col_name},p:"]
    for n in nodes_sorted:
        idx = id_to_idx[id(n)]
        # Procura pai (no mais profundo entre os usados que eh ancestral de n)
        parent = n.parent
        parent_idx = None
        while parent is not None:
            if id(parent) in id_to_idx:
                parent_idx = id_to_idx[id(parent)]
                break
            parent = parent.parent
        if parent_idx is None:
            # absoluto
            out.append(f"*{idx}={n.prefix()}")
        else:
            # encadeado: parent_prefix + ext
            parent_node = next(p for p in nodes_sorted if id_to_idx[id(p)] == parent_idx)
            ext = n.prefix()[len(parent_node.prefix()):]
            out.append(f"*{idx}={parent_idx}+{ext}")

    for node, suffix in decomp:
        if node is None:
            out.append(f"\\!{suffix}")
        else:
            out.append(f"{id_to_idx[id(node)]} {suffix}")
    return "\n".join(out) + "\n"


def encode_prefix_V3(strings, col_name="col"):
    """Inline: 1a aparicao de cada prefix declara + emite junto.

    Linha pode ser:
      *<text> <suffix>          ← decl absoluta + emite
      *<idx>+<ext> <suffix>     ← decl encadeada + emite
      <idx> <suffix>            ← uso direto
      \\!<full>                  ← excecao
    """
    nodes, decomp = optimize_trie_selection(strings)

    # Numerar pela ordem de PRIMEIRO USO no decomp
    first_use_order = []
    seen = set()
    for node, _ in decomp:
        if node is not None and id(node) not in seen:
            seen.add(id(node))
            first_use_order.append(node)

    id_to_idx = {id(n): i + 1 for i, n in enumerate(first_use_order)}

    out = [f"{col_name},p:"]
    declared = set()

    for node, suffix in decomp:
        if node is None:
            out.append(f"\\!{suffix}")
            continue
        idx = id_to_idx[id(node)]
        if idx not in declared:
            # 1a aparicao deste node — declara + emite
            # Procura ancestral declarado
            parent = node.parent
            parent_idx = None
            while parent is not None:
                if id(parent) in id_to_idx and id_to_idx[id(parent)] in declared:
                    parent_idx = id_to_idx[id(parent)]
                    break
                parent = parent.parent
            if parent_idx is None:
                out.append(f"*{node.prefix()} {suffix}")
            else:
                parent_node = next(p for p in first_use_order
                                    if id_to_idx[id(p)] == parent_idx)
                ext = node.prefix()[len(parent_node.prefix()):]
                out.append(f"*{parent_idx}+{ext} {suffix}")
            declared.add(idx)
        else:
            out.append(f"{idx} {suffix}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Encoder SUFFIX — espelhado
# ---------------------------------------------------------------------------

def encode_suffix_V1(strings, col_name="col"):
    """Suffix V1: trie em strings revertidas, header com sufixos absolutos."""
    rev = [s[::-1] for s in strings]
    nodes_rev, decomp_rev = optimize_trie_selection(rev)

    # Os "prefixos" da rev sao na verdade SUFIXOS das originais
    id_to_idx = {id(n): i + 1 for i, n in enumerate(nodes_rev)}

    out = [f"{col_name},s:"]
    for n in nodes_rev:
        # Reverter prefix da rev = suffix da string original
        suffix_real = n.prefix()[::-1]
        out.append(f"*{id_to_idx[id(n)]}={suffix_real}")

    for (node, suffix_rev), original in zip(decomp_rev, strings):
        if node is None:
            out.append(f"\\!{original}")
        else:
            # var = parte da string original que NAO eh sufixo
            var = suffix_rev[::-1]
            out.append(f"{id_to_idx[id(node)]} {var}")
    return "\n".join(out) + "\n"


def encode_suffix_V2(strings, col_name="col"):
    """Suffix V2: encadeado."""
    rev = [s[::-1] for s in strings]
    nodes_rev, decomp_rev = optimize_trie_selection(rev)

    nodes_sorted = sorted(nodes_rev, key=lambda n: (n.depth, -n.count))
    id_to_idx = {id(n): i + 1 for i, n in enumerate(nodes_sorted)}

    out = [f"{col_name},s:"]
    for n in nodes_sorted:
        idx = id_to_idx[id(n)]
        parent = n.parent
        parent_idx = None
        while parent is not None:
            if id(parent) in id_to_idx:
                parent_idx = id_to_idx[id(parent)]
                break
            parent = parent.parent
        suffix_real = n.prefix()[::-1]
        if parent_idx is None:
            out.append(f"*{idx}={suffix_real}")
        else:
            parent_node = next(p for p in nodes_sorted if id_to_idx[id(p)] == parent_idx)
            parent_suffix = parent_node.prefix()[::-1]
            # ext: chars que estao em suffix_real mas nao em parent_suffix
            # Como suffix_real eh maior (parent eh ancestral em rev), parent_suffix eh sufixo de suffix_real
            ext = suffix_real[:-len(parent_suffix)] if parent_suffix else suffix_real
            out.append(f"*{idx}={parent_idx}+{ext}")

    for (node, suffix_rev), original in zip(decomp_rev, strings):
        if node is None:
            out.append(f"\\!{original}")
        else:
            var = suffix_rev[::-1]
            out.append(f"{id_to_idx[id(node)]} {var}")
    return "\n".join(out) + "\n"


def encode_suffix_V3(strings, col_name="col"):
    """Suffix V3: inline."""
    rev = [s[::-1] for s in strings]
    nodes_rev, decomp_rev = optimize_trie_selection(rev)

    first_use_order = []
    seen = set()
    for node, _ in decomp_rev:
        if node is not None and id(node) not in seen:
            seen.add(id(node))
            first_use_order.append(node)
    id_to_idx = {id(n): i + 1 for i, n in enumerate(first_use_order)}

    out = [f"{col_name},s:"]
    declared = set()

    for (node, suffix_rev), original in zip(decomp_rev, strings):
        if node is None:
            out.append(f"\\!{original}")
            continue
        idx = id_to_idx[id(node)]
        var = suffix_rev[::-1]
        if idx not in declared:
            # 1a aparicao
            parent = node.parent
            parent_idx = None
            while parent is not None:
                if id(parent) in id_to_idx and id_to_idx[id(parent)] in declared:
                    parent_idx = id_to_idx[id(parent)]
                    break
                parent = parent.parent
            suffix_real = node.prefix()[::-1]
            if parent_idx is None:
                out.append(f"*{suffix_real} {var}")
            else:
                parent_node = next(p for p in first_use_order
                                    if id_to_idx[id(p)] == parent_idx)
                parent_suffix = parent_node.prefix()[::-1]
                ext = suffix_real[:-len(parent_suffix)] if parent_suffix else suffix_real
                out.append(f"*{parent_idx}+{ext} {var}")
            declared.add(idx)
        else:
            out.append(f"{idx} {var}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Decoders
# ---------------------------------------------------------------------------

def decode_prefix_V1_or_V2(text):
    """Funciona para V1 (absoluto) e V2 (encadeado)."""
    lines = text.splitlines()
    prefix_dict: dict[int, str] = {}
    body = []
    for i, line in enumerate(lines):
        if i == 0 or not line:
            continue
        if line.startswith("*"):
            # Decl: *idx=valor ou *idx=parent+ext
            eq = line.index("=")
            idx = int(line[1:eq])
            rhs = line[eq+1:]
            if "+" in rhs and rhs.split("+")[0].isdigit():
                parent_idx, ext = rhs.split("+", 1)
                prefix_dict[idx] = prefix_dict[int(parent_idx)] + ext
            else:
                prefix_dict[idx] = rhs
        else:
            body.append(line)

    out = []
    for line in body:
        if line.startswith("\\!"):
            out.append(line[2:])
        else:
            idx_str, var = line.split(" ", 1)
            idx = int(idx_str)
            out.append(prefix_dict[idx] + var)
    return out


def decode_prefix_V3(text):
    """Inline: declaracoes embebidas no body."""
    lines = text.splitlines()
    prefix_dict: dict[int, str] = {}
    next_idx = 1
    out = []
    for i, line in enumerate(lines):
        if i == 0 or not line:
            continue
        if line.startswith("\\!"):
            out.append(line[2:])
            continue
        if line.startswith("*"):
            # Inline decl: *<text> <suffix> ou *<idx>+<ext> <suffix>
            rest = line[1:]
            sp = rest.index(" ")
            decl = rest[:sp]
            suffix = rest[sp+1:]
            if "+" in decl and decl.split("+")[0].isdigit():
                parent_idx, ext = decl.split("+", 1)
                prefix = prefix_dict[int(parent_idx)] + ext
            else:
                prefix = decl
            prefix_dict[next_idx] = prefix
            out.append(prefix + suffix)
            next_idx += 1
        else:
            idx_str, var = line.split(" ", 1)
            idx = int(idx_str)
            out.append(prefix_dict[idx] + var)
    return out


def decode_suffix_V1_or_V2(text):
    lines = text.splitlines()
    suffix_dict: dict[int, str] = {}
    body = []
    for i, line in enumerate(lines):
        if i == 0 or not line:
            continue
        if line.startswith("*"):
            eq = line.index("=")
            idx = int(line[1:eq])
            rhs = line[eq+1:]
            if "+" in rhs and rhs.split("+")[0].isdigit():
                parent_idx, ext = rhs.split("+", 1)
                # No suffix mode encadeado, ext eh o que vai ANTES do parent
                # (em rev, ext eh prefixo)
                suffix_dict[idx] = ext + suffix_dict[int(parent_idx)]
            else:
                suffix_dict[idx] = rhs
        else:
            body.append(line)
    out = []
    for line in body:
        if line.startswith("\\!"):
            out.append(line[2:])
        else:
            idx_str, var = line.split(" ", 1)
            idx = int(idx_str)
            out.append(var + suffix_dict[idx])
    return out


def decode_suffix_V3(text):
    lines = text.splitlines()
    suffix_dict: dict[int, str] = {}
    next_idx = 1
    out = []
    for i, line in enumerate(lines):
        if i == 0 or not line:
            continue
        if line.startswith("\\!"):
            out.append(line[2:])
            continue
        if line.startswith("*"):
            rest = line[1:]
            sp = rest.index(" ")
            decl = rest[:sp]
            var = rest[sp+1:]
            if "+" in decl and decl.split("+")[0].isdigit():
                parent_idx, ext = decl.split("+", 1)
                suffix = ext + suffix_dict[int(parent_idx)]
            else:
                suffix = decl
            suffix_dict[next_idx] = suffix
            out.append(var + suffix)
            next_idx += 1
        else:
            idx_str, var = line.split(" ", 1)
            idx = int(idx_str)
            out.append(var + suffix_dict[idx])
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def csv_encode(rows):
    if not rows:
        return ""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                        lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def gz(text: str) -> bytes:
    return gzip.compress(text.encode("utf-8"), compresslevel=9)


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

def E1():
    return ["user057@gmail.com", "user026@outlook.com", "user005@outlook.com",
             "user013@yahoo.com", "user061@yahoo.com", "user024@gmail.com",
             "user022@yahoo.com"]


def E2():
    out = []
    for i in range(50): out.append(f"user{i:03d}@gmail.com")
    for i in range(50): out.append(f"user{i+50:03d}@yahoo.com")
    random.shuffle(out)
    return out


def E3():
    domains = ["@gmail.com", "@yahoo.com", "@outlook.com"]
    out = [f"user{i:03d}{domains[i % 3]}" for i in range(100)]
    random.shuffle(out)
    return out


def E4():
    prefixes = ["INV-2026-", "PED-2026-", "REQ-2026-"]
    out = [f"{prefixes[i % 3]}{i:04d}" for i in range(100)]
    random.shuffle(out)
    return out


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def test_variant(values, encoder_fn, decoder_fn, name):
    text = encoder_fn(values, col_name="col")
    bytes_n = len(text.encode("utf-8"))
    bytes_gz = len(gz(text))
    try:
        decoded = decoder_fn(text)
        rt = decoded == values
    except Exception as e:
        rt = False
    return text, bytes_n, bytes_gz, rt


def run_scenario(name, values):
    print("=" * 96)
    print(f"[{name}] {len(values)} valores")
    print("=" * 96)

    # CSV
    rows = [{"col": v} for v in values]
    csv_text = csv_encode(rows)
    b_csv = len(csv_text.encode("utf-8"))
    b_csv_gz = len(gz(csv_text))

    # SRDMP referencia
    srdmp_text = tcf_encode(rows, flags=Flags(S=True, R=True, D=True, M=True, P=True))
    b_srdmp = len(srdmp_text.encode("utf-8"))
    b_srdmp_gz = len(gz(srdmp_text))

    # 6 variantes (3 prefix + 3 suffix)
    variants = [
        ("prefix-V1", encode_prefix_V1, decode_prefix_V1_or_V2),
        ("prefix-V2", encode_prefix_V2, decode_prefix_V1_or_V2),
        ("prefix-V3", encode_prefix_V3, decode_prefix_V3),
        ("suffix-V1", encode_suffix_V1, decode_suffix_V1_or_V2),
        ("suffix-V2", encode_suffix_V2, decode_suffix_V1_or_V2),
        ("suffix-V3", encode_suffix_V3, decode_suffix_V3),
    ]

    print(f"\n  csv: {b_csv}B  csv+gz: {b_csv_gz}B  srdmp: {b_srdmp}B  srdmp+gz: {b_srdmp_gz}B")
    print(f"\n  {'variante':<14} {'bytes':>6} {'+gz':>6} {'vs srdmp':>10} {'vs csv':>10} {'rt':>4}")
    print(f"  {'-'*14} {'-'*6} {'-'*6} {'-'*10} {'-'*10} {'-'*4}")

    results = {"name": name, "n": len(values),
                "csv": b_csv, "csv_gz": b_csv_gz,
                "srdmp": b_srdmp, "srdmp_gz": b_srdmp_gz,
                "variants": {}}

    scen_dir = OUT / name
    scen_dir.mkdir(exist_ok=True)
    (scen_dir / "source.csv").write_text(csv_text, encoding="utf-8")
    (scen_dir / "tcf-srdmp.tcf").write_text(srdmp_text, encoding="utf-8")

    for vname, enc_fn, dec_fn in variants:
        text, b, b_gz, rt = test_variant(values, enc_fn, dec_fn, vname)
        vs_srdmp = (b/b_srdmp - 1)*100 if b_srdmp else 0
        vs_csv = (b/b_csv - 1)*100 if b_csv else 0
        rt_str = "OK" if rt else "FAIL"
        print(f"  {vname:<14} {b:>6} {b_gz:>6} {vs_srdmp:>+8.1f}% {vs_csv:>+8.1f}% {rt_str:>4}")
        results["variants"][vname] = {
            "bytes": b, "bytes_gz": b_gz,
            "vs_srdmp_pct": vs_srdmp, "vs_csv_pct": vs_csv,
            "roundtrip": rt,
        }
        (scen_dir / f"{vname}.txt").write_text(text, encoding="utf-8")

    # Mostra prefix-V3 + suffix-V3 (variantes mais compactas) para inspecao
    for v in ["prefix-V3", "suffix-V3"]:
        text = (scen_dir / f"{v}.txt").read_text(encoding="utf-8")
        print(f"\n  --- {v} (primeiras 10 linhas) ---")
        for line in text.splitlines()[:10]:
            print(f"    {line}")

    return results


def main():
    print("\n" + "=" * 96)
    print("Lab dirty (parte 2): trie com 3 variantes × 2 direcoes (prefix/suffix)")
    print("=" * 96)

    all_results = []
    all_results.append(run_scenario("E1-user-example", E1()))
    all_results.append(run_scenario("E2-emails-2dominios", E2()))
    all_results.append(run_scenario("E3-emails-3dominios", E3()))
    all_results.append(run_scenario("E4-codigos-3prefixes", E4()))

    # Sintese
    print("\n" + "=" * 96)
    print("Sintese — melhor variante por cenario")
    print("=" * 96)
    print(f"\n  {'cenario':<22} {'srdmp':>6} {'pV1':>5} {'pV2':>5} {'pV3':>5} "
          f"{'sV1':>5} {'sV2':>5} {'sV3':>5} {'best':<10}")
    print(f"  {'-'*22} {'-'*6} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*10}")
    for r in all_results:
        v = r["variants"]
        all_var = {**{"srdmp": r["srdmp"]}, **{k: v[k]["bytes"] for k in v}}
        best = min(all_var, key=all_var.get)
        print(f"  {r['name']:<22} {r['srdmp']:>6} "
              f"{v['prefix-V1']['bytes']:>5} {v['prefix-V2']['bytes']:>5} "
              f"{v['prefix-V3']['bytes']:>5} {v['suffix-V1']['bytes']:>5} "
              f"{v['suffix-V2']['bytes']:>5} {v['suffix-V3']['bytes']:>5} "
              f"{best:<10}")

    # Roundtrip stats
    print("\n  Roundtrip (deve ser 100% OK):")
    for r in all_results:
        all_ok = all(v["roundtrip"] for v in r["variants"].values())
        print(f"    {r['name']:<22} {'OK' if all_ok else 'FAIL'}")

    # Salva
    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
