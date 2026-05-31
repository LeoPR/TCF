"""Lab dirty: trie de prefixos compartilhados.

Implementa Variante 1 (header com prefix declarations + body com refs).
Compara com SRDMP atual e CSV em 3 cenarios de email.

Saida: ./output/
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
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Trie
# ---------------------------------------------------------------------------

@dataclass
class TrieNode:
    char: str = ""
    parent: "TrieNode | None" = None
    children: dict = field(default_factory=dict)
    count: int = 0
    is_end: bool = False  # alguma string termina aqui

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


def build_trie(strings: list[str]) -> TrieNode:
    root = TrieNode()
    for s in strings:
        node = root
        for c in s:
            if c not in node.children:
                child = TrieNode(char=c, parent=node)
                node.children[c] = child
            node = node.children[c]
            node.count += 1
        node.is_end = True
    return root


def collect_candidate_prefixes(root: TrieNode,
                                 min_count: int = 2,
                                 min_depth: int = 4) -> list[TrieNode]:
    """DFS coletando nos com count >= min_count e depth >= min_depth."""
    out = []
    def dfs(node):
        if node.parent is not None:  # pula root
            if node.count >= min_count and node.depth >= min_depth:
                out.append(node)
        for child in node.children.values():
            dfs(child)
    dfs(root)
    return out


def filter_useful(candidates: list[TrieNode],
                   declaration_overhead: int = 4) -> list[TrieNode]:
    """Filtra: ganho > custo. Ganho = count * (depth - 2) - overhead.

    -2 porque cada uso eh `idx ` (1 char idx + 1 espaco), em vez do prefix.
    Aproximacao.
    """
    out = []
    for n in candidates:
        gain = n.count * (n.depth - 2) - declaration_overhead - len(str(n.depth))
        if gain > 0:
            out.append(n)
    return out


def select_deepest_per_string(strings: list[str],
                                trie_root: TrieNode,
                                useful_set: set[int]) -> list[tuple[TrieNode | None, str]]:
    """Para cada string, encontra o no util mais profundo que cobre prefix."""
    out = []
    for s in strings:
        node = trie_root
        deepest_useful = None
        for c in s:
            if c not in node.children:
                break
            node = node.children[c]
            if id(node) in useful_set:
                deepest_useful = node
        if deepest_useful is None:
            out.append((None, s))
        else:
            prefix = deepest_useful.prefix()
            suffix = s[len(prefix):]
            out.append((deepest_useful, suffix))
    return out


# ---------------------------------------------------------------------------
# Encoder/decoder trie
# ---------------------------------------------------------------------------

def encode_trie(strings: list[str], col_name: str = "col") -> tuple[str, list[str]]:
    """Encoda strings usando trie de prefixos.

    Variante 1 com **otimizacao**: declara so os prefixos REALMENTE usados.
    """
    if not strings:
        return f"{col_name},t:\n", []

    root = build_trie(strings)
    candidates = collect_candidate_prefixes(root, min_count=2, min_depth=4)
    useful = filter_useful(candidates)

    # Pass 1 — todos candidatos como pool
    pool_set = set(id(n) for n in useful)
    decompositions = select_deepest_per_string(strings, root, pool_set)

    # Pass 2 — descobrir quais nós foram REALMENTE escolhidos
    used_ids = {id(node) for node, _ in decompositions if node is not None}
    used_nodes = [n for n in useful if id(n) in used_ids]

    # Pass 3 — re-decompor garantindo que so usamos os "used"
    # (alguns que nao estao em used_nodes deveriam ter sido escolhidos por
    #  outro string, mas como esse nao foi mais profundo, agora cai num
    #  ancestral. Vou fazer 2-pass — refinar)
    used_set = {id(n) for n in used_nodes}
    decompositions = select_deepest_per_string(strings, root, used_set)

    # Re-checar usage apos refinement
    final_used_ids = {id(node) for node, _ in decompositions if node is not None}
    final_used_nodes = [n for n in used_nodes if id(n) in final_used_ids]

    # Numerar
    final_used_nodes.sort(key=lambda n: (-n.count, -n.depth))
    used_id_to_idx = {id(n): i + 1 for i, n in enumerate(final_used_nodes)}

    # Header
    out = [f"{col_name},t:"]
    for n in final_used_nodes:
        idx = used_id_to_idx[id(n)]
        out.append(f"*{idx}={n.prefix()}")

    # Body — re-decompor com so o set final
    final_set = {id(n) for n in final_used_nodes}
    final_decompositions = select_deepest_per_string(strings, root, final_set)

    for node, suffix in final_decompositions:
        if node is None:
            out.append(f"\\!{suffix}")
        else:
            idx = used_id_to_idx[id(node)]
            out.append(f"{idx} {suffix}")

    return "\n".join(out) + "\n", [n.prefix() for n in final_used_nodes]


def decode_trie(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines:
        return []
    # Skip header (first line: col,t:)
    # Parse prefix declarations *N=prefix
    # Parse body lines
    prefix_dict: dict[int, str] = {}
    body_lines: list[str] = []

    for i, line in enumerate(lines):
        if i == 0:
            continue  # col header
        if not line:
            continue
        if line.startswith("*"):
            # *N=prefix
            eq = line.index("=")
            idx = int(line[1:eq])
            prefix = line[eq+1:]
            prefix_dict[idx] = prefix
            continue
        body_lines.append(line)

    out = []
    for line in body_lines:
        if line.startswith("\\!"):
            out.append(line[2:])
            continue
        # "<idx> <suffix>"
        if " " in line:
            idx_str, suffix = line.split(" ", 1)
            idx = int(idx_str)
            out.append(prefix_dict[idx] + suffix)
        else:
            # so idx (suffix vazio?)
            idx = int(line)
            out.append(prefix_dict[idx])

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

def E1_user_example():
    """Exemplo literal do user (7 emails)."""
    return [
        "user057@gmail.com",
        "user026@outlook.com",
        "user005@outlook.com",
        "user013@yahoo.com",
        "user061@yahoo.com",
        "user024@gmail.com",
        "user022@yahoo.com",
    ]


def E2_emails_2dominios():
    """100 emails 50/50."""
    out = []
    for i in range(50):
        out.append(f"user{i:03d}@gmail.com")
    for i in range(50):
        out.append(f"user{i+50:03d}@yahoo.com")
    random.shuffle(out)
    return out


def E3_emails_3dominios():
    """100 emails em 3 dominios."""
    domains = ["@gmail.com", "@yahoo.com", "@outlook.com"]
    out = []
    for i in range(100):
        out.append(f"user{i:03d}{domains[i % 3]}")
    random.shuffle(out)
    return out


def E4_codigos_3prefixes():
    """100 codigos em 3 prefixes."""
    prefixes = ["INV-2026-", "PED-2026-", "REQ-2026-"]
    out = []
    for i in range(100):
        out.append(f"{prefixes[i % 3]}{i:04d}")
    random.shuffle(out)
    return out


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_scenario(name: str, values: list[str], col_name: str = "col"):
    print("=" * 92)
    print(f"[{name}] {len(values)} valores")
    print("=" * 92)

    # CSV
    rows = [{col_name: v} for v in values]
    csv_text = csv_encode(rows)
    b_csv = len(csv_text.encode("utf-8"))
    b_csv_gz = len(gz(csv_text))

    # TCF SRDMP atual
    text_srdmp = tcf_encode(rows, flags=Flags(S=True, R=True, D=True, M=True, P=True))
    b_srdmp = len(text_srdmp.encode("utf-8"))
    b_srdmp_gz = len(gz(text_srdmp))

    # Trie
    trie_text, prefixes = encode_trie(values, col_name=col_name)
    b_trie = len(trie_text.encode("utf-8"))
    b_trie_gz = len(gz(trie_text))

    # Roundtrip trie
    try:
        decoded = decode_trie(trie_text)
        rt_trie = decoded == values
        rt_msg = "OK" if rt_trie else f"FAIL ({len(decoded)} != {len(values)})"
    except Exception as e:
        rt_trie = False
        rt_msg = f"FAIL — {type(e).__name__}: {e}"

    print(f"\n  bytes:")
    print(f"    csv:        {b_csv:>5}  csv+gz   {b_csv_gz:>5}")
    print(f"    SRDMP:      {b_srdmp:>5}  +gz      {b_srdmp_gz:>5}")
    print(f"    trie:       {b_trie:>5}  +gz      {b_trie_gz:>5}  ({(b_trie/b_srdmp-1)*100:+.1f}% vs SRDMP)")
    print(f"\n  prefixes detectados ({len(prefixes)}): {prefixes[:5]}{'...' if len(prefixes)>5 else ''}")
    print(f"  roundtrip trie: {rt_msg}")

    # Mostra primeiras 15 linhas
    print(f"\n  --- trie output (primeiras 15 linhas) ---")
    for line in trie_text.splitlines()[:15]:
        print(f"    {line}")
    if len(trie_text.splitlines()) > 15:
        print(f"    ... ({len(trie_text.splitlines())-15} linhas a mais)")

    # Salva
    scen_dir = OUT / name
    scen_dir.mkdir(exist_ok=True)
    (scen_dir / "source.csv").write_text(csv_text, encoding="utf-8")
    (scen_dir / "tcf-SRDMP.tcf").write_text(text_srdmp, encoding="utf-8")
    (scen_dir / "tcf-trie.txt").write_text(trie_text, encoding="utf-8")

    return {
        "name": name,
        "n": len(values),
        "csv": b_csv, "csv_gz": b_csv_gz,
        "srdmp": b_srdmp, "srdmp_gz": b_srdmp_gz,
        "trie": b_trie, "trie_gz": b_trie_gz,
        "trie_vs_srdmp_pct": (b_trie/b_srdmp - 1)*100 if b_srdmp else 0,
        "trie_vs_csv_pct": (b_trie/b_csv - 1)*100 if b_csv else 0,
        "prefixes_count": len(prefixes),
        "roundtrip_trie": rt_trie,
    }


def main():
    print("\n" + "=" * 92)
    print("Lab dirty: trie de prefixos compartilhados (Variante 1)")
    print("=" * 92)

    results = []
    results.append(run_scenario("E1-user-example", E1_user_example(),
                                  col_name="email"))
    results.append(run_scenario("E2-emails-2dominios", E2_emails_2dominios(),
                                  col_name="email"))
    results.append(run_scenario("E3-emails-3dominios", E3_emails_3dominios(),
                                  col_name="email"))
    results.append(run_scenario("E4-codigos-3prefixes", E4_codigos_3prefixes(),
                                  col_name="codigo"))

    # Sintese
    print("\n" + "=" * 92)
    print("Sintese")
    print("=" * 92)
    print(f"\n  {'cenario':<26} {'csv':>5} {'SRDMP':>6} {'trie':>5} "
          f"{'trie vs SRDMP':>14} {'trie vs csv':>13} {'prefs':>6} {'rt':>4}")
    print(f"  {'-'*26} {'-'*5} {'-'*6} {'-'*5} {'-'*14} {'-'*13} {'-'*6} {'-'*4}")
    for r in results:
        rt = "OK" if r["roundtrip_trie"] else "FAIL"
        print(f"  {r['name']:<26} {r['csv']:>5} {r['srdmp']:>6} {r['trie']:>5} "
              f"{r['trie_vs_srdmp_pct']:>+12.1f}%  {r['trie_vs_csv_pct']:>+11.1f}%  "
              f"{r['prefixes_count']:>6} {rt:>4}")

    avg_vs_srdmp = sum(r["trie_vs_srdmp_pct"] for r in results) / len(results)
    avg_vs_csv = sum(r["trie_vs_csv_pct"] for r in results) / len(results)
    print(f"\n  Avg trie vs SRDMP: {avg_vs_srdmp:+.2f}%")
    print(f"  Avg trie vs CSV:   {avg_vs_csv:+.2f}%")

    summary = {"experiment": "affix-trie", "scenarios": results,
                "averages": {"vs_SRDMP": avg_vs_srdmp, "vs_CSV": avg_vs_csv}}
    (OUT / "results.json").write_text(json.dumps(summary, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
