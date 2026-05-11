"""Lab dirty: motor de compressao com variaveis expostas.

UMA funcao `compress_v(values, **params)` parametrizada. Diferentes
combinacoes reproduzem RLE, DICT, prefix-DICT, suffix-DICT, etc.

NAO eh otimizado. Nao eh decisao final. Eh exploracao.

Saida: ./output/ com tabela comparativa.
"""
from __future__ import annotations
import gzip
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Motor unificado — compress_v
# ---------------------------------------------------------------------------

@dataclass
class CompressResult:
    text: str            # output codificado
    syntax: str          # qual sintaxe usou (orienta decoder)
    config: dict         # parametros aplicados
    n_dict_entries: int  # tamanho do dict gerado


def compress_v(
    values: list[str],
    *,
    # variaveis expostas
    window: int | None = None,         # 1 = streaming; None = N
    match_kind: str = "full",          # "full" | "prefix" | "suffix" | "contiguous"
    min_length: int = 1,               # min do match (chars)
    min_count: int = 2,                # min count p/ virar entry
    search_scope: str = "all_previous",  # "all_previous" | "buffer_only" | "contiguous_only"
    direction: str = "forward",        # "forward" | "backward"
    sort_first: bool = False,
    emit_strategy: str = "inline",     # "inline" | "header" | "first_use"
) -> CompressResult:
    """Motor variavel. Despacha para sub-implementacao baseada em params."""

    config = {
        "window": window, "match_kind": match_kind,
        "min_length": min_length, "min_count": min_count,
        "search_scope": search_scope, "direction": direction,
        "sort_first": sort_first, "emit_strategy": emit_strategy,
    }

    if not values:
        return CompressResult(text="\n", syntax="empty", config=config, n_dict_entries=0)

    # Sort se pedido
    work_values = sorted(values) if sort_first else list(values)

    # Reverso se direction=backward (para suffix-mode)
    if direction == "backward":
        work_values = [v[::-1] for v in work_values]

    # ---- Despacho ----

    if match_kind == "contiguous" or search_scope == "contiguous_only":
        # RLE puro
        return _emit_rle(values, work_values, config)

    if match_kind == "full":
        if search_scope == "all_previous":
            return _emit_dict_full(values, work_values, config)
        elif search_scope == "buffer_only":
            return _emit_dict_buffered(values, work_values, config)

    if match_kind == "prefix":
        return _emit_prefix(values, work_values, config)

    if match_kind == "suffix":
        return _emit_suffix(values, work_values, config)

    raise ValueError(f"Combinacao nao suportada: {config}")


# ---------------------------------------------------------------------------
# Sub-emitters (cada um implementa uma sintaxe)
# ---------------------------------------------------------------------------

def _emit_rle(orig, vals, config):
    """RLE classico: N*val agrupando contiguos."""
    out = ["# rle"]
    if not vals:
        return CompressResult("\n".join(out)+"\n", "rle", config, 0)
    cur = vals[0]
    count = 1
    n_dict = 1
    runs = []
    for v in vals[1:]:
        if v == cur:
            count += 1
        else:
            runs.append((count, cur))
            cur = v
            count = 1
            n_dict += 1
    runs.append((count, cur))
    for c, v in runs:
        if c >= config["min_count"]:
            out.append(f"{c}*{v}")
        else:
            for _ in range(c):
                out.append(v)
    return CompressResult("\n".join(out)+"\n", "rle", config, n_dict)


def _emit_dict_full(orig, vals, config):
    """DICT por valor — declara cada novo, refs sucessivos."""
    out = ["# dict-full"]
    seen: dict[str, int] = {}
    body_lines: list[str] = []
    counts = Counter(vals)

    for v in vals:
        if v in seen:
            body_lines.append(str(seen[v]))
        else:
            if counts[v] >= config["min_count"]:
                seen[v] = len(seen) + 1
                body_lines.append(f"@{v}")  # @ marca declaracao
            else:
                body_lines.append(v)  # literal sem dict

    out.extend(body_lines)
    return CompressResult("\n".join(out)+"\n", "dict-full", config, len(seen))


def _emit_dict_buffered(orig, vals, config):
    """DICT com janela limitada (W). So olha para os ultimos W valores."""
    W = config["window"] or 32
    out = [f"# dict-buf W={W}"]
    body: list[str] = []
    recent: list[str] = []  # janela
    recent_idx: dict[str, int] = {}  # valor -> posicao no recent

    for v in vals:
        if v in recent_idx:
            # ref relativa
            pos = recent_idx[v]
            body.append(f">{len(recent) - pos}")  # quantos passos atras
        else:
            body.append(v)
            recent_idx[v] = len(recent)
            recent.append(v)
            # Mantem janela
            if len(recent) > W:
                old = recent.pop(0)
                # Reindexa (custoso mas didatico)
                recent_idx = {x: i for i, x in enumerate(recent)}
    out.extend(body)
    return CompressResult("\n".join(out)+"\n", "dict-buf", config, len(set(vals)))


def _emit_prefix(orig, vals, config):
    """Prefix-DICT: detecta LCP comum e remove."""
    if not vals or len(vals) < 2:
        return CompressResult("\n".join(["# prefix"] + vals)+"\n", "prefix", config, 0)

    # LCP global
    lcp = vals[0]
    for v in vals[1:]:
        i = 0
        while i < min(len(lcp), len(v)) and lcp[i] == v[i]:
            i += 1
        lcp = lcp[:i]
        if not lcp:
            break

    # Se LCP curto, fallback para dict-full
    if len(lcp) < config["min_length"]:
        return _emit_dict_full(orig, vals, config)

    out = [f"# prefix p=\"{lcp}\""]
    for v in vals:
        if v.startswith(lcp):
            out.append(v[len(lcp):])
        else:
            out.append(f"\\!{v}")
    return CompressResult("\n".join(out)+"\n", "prefix", config, 1)


def _emit_suffix(orig, vals, config):
    """Suffix-DICT: detecta LCS (longest common suffix) — vals ja revertidos
    se direction=backward, mas aqui assumimos forward direction com original."""
    # Trabalha em forma original
    if not orig or len(orig) < 2:
        return CompressResult("\n".join(["# suffix"] + list(orig))+"\n", "suffix", config, 0)

    # LCS via reverso
    rev = [v[::-1] for v in orig]
    lcs_rev = rev[0]
    for v in rev[1:]:
        i = 0
        while i < min(len(lcs_rev), len(v)) and lcs_rev[i] == v[i]:
            i += 1
        lcs_rev = lcs_rev[:i]
        if not lcs_rev:
            break
    lcs = lcs_rev[::-1]

    if len(lcs) < config["min_length"]:
        return _emit_dict_full(orig, list(orig), config)

    out = [f"# suffix s=\"{lcs}\""]
    for v in orig:
        if v.endswith(lcs):
            out.append(v[:-len(lcs)])
        else:
            out.append(f"\\!{v}")
    return CompressResult("\n".join(out)+"\n", "suffix", config, 1)


# ---------------------------------------------------------------------------
# Decoders (1 por sintaxe, simples)
# ---------------------------------------------------------------------------

def decode(text: str, syntax: str) -> list[str]:
    lines = text.splitlines()
    if not lines:
        return []
    head = lines[0].strip()
    body = lines[1:]

    if syntax == "rle":
        out = []
        for line in body:
            if "*" in line and line[0].isdigit():
                idx = line.index("*")
                count = int(line[:idx])
                v = line[idx+1:]
                out.extend([v] * count)
            else:
                out.append(line)
        return out

    if syntax == "dict-full":
        out = []
        dict_entries: list[str] = []
        for line in body:
            if line.startswith("@"):
                v = line[1:]
                dict_entries.append(v)
                out.append(v)
            elif line.isdigit():
                idx = int(line)
                out.append(dict_entries[idx - 1])
            else:
                out.append(line)
        return out

    if syntax == "dict-buf":
        out = []
        recent: list[str] = []
        for line in body:
            if line.startswith(">"):
                steps = int(line[1:])
                v = recent[-steps]
                out.append(v)
                recent.append(v)
            else:
                out.append(line)
                recent.append(line)
        return out

    if syntax == "prefix":
        # head: # prefix p="..."
        prefix = ""
        if "p=\"" in head:
            start = head.index("p=\"") + 3
            end = head.rindex("\"")
            prefix = head[start:end]
        out = []
        for line in body:
            if line.startswith("\\!"):
                out.append(line[2:])
            else:
                out.append(prefix + line)
        return out

    if syntax == "suffix":
        suffix = ""
        if "s=\"" in head:
            start = head.index("s=\"") + 3
            end = head.rindex("\"")
            suffix = head[start:end]
        out = []
        for line in body:
            if line.startswith("\\!"):
                out.append(line[2:])
            else:
                out.append(line + suffix)
        return out

    raise ValueError(f"Sintaxe desconhecida: {syntax}")


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

def C1_rle_friendly():
    return ["Ana", "Ana", "Bob", "Bob", "Bob", "Carol", "Carol", "Carol"]


def C2_categorical():
    import random
    random.seed(42)
    cats = ["red", "blue", "green", "yellow"]
    return [random.choice(cats) for _ in range(30)]


def C3_codigos_prefix():
    return [f"PED-2026-{i:04d}" for i in range(1, 21)]


def C4_emails_3dom():
    domains = ["@gmail.com", "@yahoo.com", "@outlook.com"]
    return [f"user{i:03d}{domains[i % 3]}" for i in range(20)]


def C5_sem_padrao():
    import random
    random.seed(42)
    chars = "abcdefghijklmnop"
    return ["".join(random.choices(chars, k=8)) for _ in range(20)]


SCENARIOS = [
    ("C1-rle-friendly", C1_rle_friendly()),
    ("C2-categorical-30", C2_categorical()),
    ("C3-codigos-prefix", C3_codigos_prefix()),
    ("C4-emails-3dom", C4_emails_3dom()),
    ("C5-sem-padrao", C5_sem_padrao()),
]


# ---------------------------------------------------------------------------
# Configuracoes nomeadas
# ---------------------------------------------------------------------------

CONFIGS = [
    ("rle",        dict(window=1, match_kind="contiguous", search_scope="contiguous_only")),
    ("dict-full",  dict(match_kind="full", search_scope="all_previous")),
    ("dict-buf-8", dict(match_kind="full", search_scope="buffer_only", window=8)),
    ("prefix",     dict(match_kind="prefix", min_length=4, sort_first=True)),
    ("suffix",     dict(match_kind="suffix", min_length=4)),
]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def gz(text: str) -> bytes:
    return gzip.compress(text.encode("utf-8"), compresslevel=9)


def main():
    print("=" * 90)
    print("Motor de compressao com variaveis — exploracao do espaco")
    print("=" * 90)

    all_results = []

    for scen_name, values in SCENARIOS:
        print("\n" + "=" * 90)
        print(f"[{scen_name}] {len(values)} valores")
        print("=" * 90)

        # Baseline: literal puro (newline-joined)
        literal = "\n".join(values) + "\n"
        b_lit = len(literal.encode("utf-8"))
        b_lit_gz = len(gz(literal))

        scen_dir = OUT / scen_name
        scen_dir.mkdir(exist_ok=True)
        (scen_dir / "literal.txt").write_text(literal, encoding="utf-8")

        print(f"\n  baseline literal: {b_lit}B  (+gz: {b_lit_gz}B)")
        print(f"\n  {'config':<14} {'syntax':<10} {'bytes':>6} {'+gz':>5} "
              f"{'vs lit':>9} {'rt':>4}")
        print(f"  {'-'*14} {'-'*10} {'-'*6} {'-'*5} {'-'*9} {'-'*4}")

        scen_results = {"name": scen_name, "n": len(values),
                          "literal_bytes": b_lit, "literal_gz": b_lit_gz,
                          "configs": {}}

        for cname, params in CONFIGS:
            try:
                result = compress_v(values, **params)
                b = len(result.text.encode("utf-8"))
                b_gz = len(gz(result.text))
                vs_lit = (b/b_lit - 1)*100 if b_lit else 0
                # Roundtrip
                try:
                    decoded = decode(result.text, result.syntax)
                    rt = decoded == values
                except Exception as e:
                    rt = False
                rt_str = "OK" if rt else "FAIL"
                sign = "+" if vs_lit >= 0 else ""
                print(f"  {cname:<14} {result.syntax:<10} {b:>6} {b_gz:>5} "
                      f"{sign}{vs_lit:>+7.1f}% {rt_str:>4}")
                (scen_dir / f"{cname}.txt").write_text(result.text, encoding="utf-8")
                scen_results["configs"][cname] = {
                    "syntax": result.syntax,
                    "bytes": b, "bytes_gz": b_gz,
                    "vs_lit_pct": vs_lit,
                    "n_dict_entries": result.n_dict_entries,
                    "roundtrip": rt,
                }
            except Exception as e:
                print(f"  {cname:<14} ERRO: {type(e).__name__}: {e}")
                scen_results["configs"][cname] = {"error": str(e)}

        all_results.append(scen_results)

    # ---- Sintese ----
    print("\n" + "=" * 90)
    print("Sintese — bytes por configuracao × cenario")
    print("=" * 90)
    print(f"\n  {'cenario':<22} {'lit':>5} ", end="")
    for cname, _ in CONFIGS:
        print(f"{cname:>10} ", end="")
    print()
    print(f"  {'-'*22} {'-'*5} " + " ".join("-"*10 for _ in CONFIGS))
    for r in all_results:
        print(f"  {r['name']:<22} {r['literal_bytes']:>5} ", end="")
        for cname, _ in CONFIGS:
            c = r["configs"].get(cname, {})
            if "bytes" in c:
                print(f"{c['bytes']:>10} ", end="")
            else:
                print(f"{'(err)':>10} ", end="")
        print()

    # Roundtrip
    print("\n  Roundtrip:")
    all_ok = True
    for r in all_results:
        for cname, c in r["configs"].items():
            if "roundtrip" in c and not c["roundtrip"]:
                print(f"    FAIL: {r['name']} / {cname}")
                all_ok = False
    print(f"  {'  TUDO OK' if all_ok else '  HA FALHAS'}")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")

    # ---- Reflexao ----
    print("\n" + "=" * 90)
    print("Reflexao: configuracoes reproduzem tecnicas conhecidas?")
    print("=" * 90)
    print("""
  rle          — esperado vencer em C1 (RLE-friendly)
  dict-full    — esperado vencer em C2 (categorical denso)
  dict-buf-8   — competidor de dict-full em C2; pior em outros
  prefix       — esperado vencer em C3 (codigos com prefix)
  suffix       — esperado vencer em C4 (emails com sufixo)
  todos        — perdem em C5 (sem padrao)

  Se isso bate empiricamente: motor com variaveis expostas reproduz
  as 4-5 tecnicas classicas. Confirmado teoricamente.

  Onde NAO bate: variavel nao tem efeito esperado ou implementacao
  tem bug. Anotar para revisar.
""")


if __name__ == "__main__":
    main()
