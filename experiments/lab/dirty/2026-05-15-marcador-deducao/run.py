"""Lab dirty: marcadores deduzidos por recorrencia.

Testa hipotese de que declarar modo no cabecalho economiza bytes
nos casos comuns. 2 sintaxes em cada cenario:
  - explicit: marcadores em todas linhas (=, *, etc.)
  - deducao: cabecalho declara modo; default omitido; marcadores so
              para excecoes

4 cenarios: cada um com modo dominante diferente.

Saida: ./output/<C>/
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
# Helpers
# ---------------------------------------------------------------------------

def lcp(values):
    if not values:
        return ""
    p = values[0]
    for v in values[1:]:
        i = 0
        while i < min(len(p), len(v)) and p[i] == v[i]:
            i += 1
        p = p[:i]
        if not p:
            break
    return p


def lcs(values):
    rev = [v[::-1] for v in values]
    return lcp(rev)[::-1]


def detect_dominant_mode(values):
    """Conta quais marcadores se aplicariam em quantas linhas e escolhe."""
    n = len(values)
    if n == 0:
        return "literal", {}

    # 1. Quantas linhas duplicadas (=N)
    seen = {}
    n_dup = 0
    for v in values:
        if v in seen:
            n_dup += 1
        else:
            seen[v] = True
    coverage_eq = n_dup / n

    # 2. Cobertura de prefix
    p = lcp(values)
    n_prefix = sum(1 for v in values if v.startswith(p)) if len(p) >= 4 else 0
    coverage_prefix = n_prefix / n if len(p) >= 4 else 0

    # 3. Cobertura de suffix
    s = lcs(values)
    n_suffix = sum(1 for v in values if v.endswith(s)) if len(s) >= 4 else 0
    coverage_suffix = n_suffix / n if len(s) >= 4 else 0

    candidates = [
        ("=", coverage_eq, {}),
        (">", coverage_prefix, {"prefix": p}),
        ("<", coverage_suffix, {"suffix": s}),
    ]
    best = max(candidates, key=lambda c: c[1])
    if best[1] < 0.3:
        return "literal", {}
    return best[0], best[2]


# ---------------------------------------------------------------------------
# Encoder explicit (todos marcadores)
# ---------------------------------------------------------------------------

def encode_explicit(values):
    """Marcadores explicitos em todas as linhas.

    `=N` para ref linha
    `*<text>` para decl inline de prefix/suffix
    `\\!<text>` para literal puro
    `<idx> <text>` para ref de string-dict
    """
    out = ["col:"]  # header sem modo
    seen_lines: dict[str, int] = {}
    p = lcp(values)
    s = lcs(values)
    use_p = len(p) >= 4
    use_s = len(s) >= 4
    declared_p = False
    declared_s = False

    for i, v in enumerate(values, 1):
        if v in seen_lines:
            out.append(f"={seen_lines[v]}")
            continue
        seen_lines[v] = i

        has_p = use_p and v.startswith(p)
        has_s = use_s and v.endswith(s)

        if has_p and has_s:
            mid = v[len(p):]
            mid = mid[:-len(s)] if s else mid
            p_part = "*1" if not declared_p else "1"
            if not declared_p:
                p_part = f"*{p}"; declared_p = True
            else:
                p_part = "*1"  # ref idx 1
            s_part = f"*{s}" if not declared_s else "*2"
            if not declared_s and use_s:
                s_part = f"*{s}"; declared_s = True
            else:
                s_part = "*2"
            out.append(f"{p_part} {mid} {s_part}")
        elif has_p:
            mid = v[len(p):]
            if not declared_p:
                out.append(f"*{p} {mid}"); declared_p = True
            else:
                out.append(f"*1 {mid}")
        elif has_s:
            pre = v[:-len(s)] if s else v
            if not declared_s:
                out.append(f"{pre} *{s}"); declared_s = True
            else:
                out.append(f"{pre} *2")
        else:
            out.append(f"\\!{v}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Encoder deducao (modo no header; default omitido)
# ---------------------------------------------------------------------------

def encode_deducao(values):
    """Cabecalho declara modo dominante. Linhas comuns sao curtas."""
    mode, info = detect_dominant_mode(values)

    if mode == "literal":
        # Sem padrao; literais
        out = ["col:"]
        for v in values:
            out.append(v)
        return "\n".join(out) + "\n"

    if mode == "=":
        # Default = ref linha. Numero sozinho = ref.
        out = ["col,=:"]
        seen_lines: dict[str, int] = {}
        for i, v in enumerate(values, 1):
            if v in seen_lines:
                out.append(str(seen_lines[v]))  # SEM `=` (default mode)
            else:
                seen_lines[v] = i
                out.append(v)
        return "\n".join(out) + "\n"

    if mode == ">":
        p = info["prefix"]
        # Default = prefix + var. 1a linha declara.
        out = [f"col,>:"]
        declared = False
        seen_lines: dict[str, int] = {}
        for i, v in enumerate(values, 1):
            if v in seen_lines:
                out.append(f"={seen_lines[v]}")  # excecao com `=`
                continue
            seen_lines[v] = i
            if v.startswith(p):
                suffix = v[len(p):]
                if not declared:
                    out.append(f"*{p} {suffix}")  # decl
                    declared = True
                else:
                    out.append(suffix)  # so o suffix (default mode = prefix+var)
            else:
                out.append(f"\\!{v}")
        return "\n".join(out) + "\n"

    if mode == "<":
        s = info["suffix"]
        out = [f"col,<:"]
        declared = False
        seen_lines: dict[str, int] = {}
        for i, v in enumerate(values, 1):
            if v in seen_lines:
                out.append(f"={seen_lines[v]}")
                continue
            seen_lines[v] = i
            if v.endswith(s):
                pre = v[:-len(s)] if s else v
                if not declared:
                    out.append(f"{pre} *{s}")
                    declared = True
                else:
                    out.append(pre)  # so prefix-var
            else:
                out.append(f"\\!{v}")
        return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Decoders
# ---------------------------------------------------------------------------

def decode_deducao(text):
    """Decoder unico que detecta modo do cabecalho."""
    lines = text.splitlines()
    if not lines:
        return []
    head = lines[0]
    body = lines[1:]

    # Detecta modo
    if head.startswith("col,=:"):
        mode = "="
    elif head.startswith("col,>:"):
        mode = ">"
    elif head.startswith("col,<:"):
        mode = "<"
    else:
        mode = "literal"

    out = []
    line_idx_to_value: dict[int, str] = {}
    declared_p = ""
    declared_s = ""

    for i, line in enumerate(body, 1):
        if not line:
            continue

        if line.startswith("="):
            ref = int(line[1:])
            v = line_idx_to_value[ref]
        elif line.startswith("\\!"):
            v = line[2:]
        elif mode == "=" and line.isdigit():
            ref = int(line)
            v = line_idx_to_value[ref]
        elif mode == ">":
            if line.startswith("*"):
                # decl inline: *prefix suffix
                rest = line[1:]
                sp = rest.index(" ")
                declared_p = rest[:sp]
                v = declared_p + rest[sp+1:]
            else:
                # so suffix; usa prefix declarado
                v = declared_p + line
        elif mode == "<":
            if "*" in line:
                # decl: <pre> *<suffix>
                sp = line.rindex(" *")
                pre = line[:sp]
                declared_s = line[sp+2:]
                v = pre + declared_s
            else:
                v = line + declared_s
        else:
            v = line

        out.append(v)
        line_idx_to_value[i] = v

    return out


def decode_explicit(text):
    """Decoder explicit. Mais ramificacoes."""
    lines = text.splitlines()
    if not lines:
        return []
    body = lines[1:]
    out = []
    line_idx_to_value: dict[int, str] = {}
    declared_p = ""
    declared_s = ""

    for i, line in enumerate(body, 1):
        if not line:
            continue
        if line.startswith("="):
            ref = int(line[1:])
            v = line_idx_to_value[ref]
        elif line.startswith("\\!"):
            v = line[2:]
        elif line.startswith("*"):
            # decl inline
            rest = line[1:]
            if " " in rest:
                # *prefix suffix
                sp = rest.index(" ")
                first = rest[:sp]
                second = rest[sp+1:]
                if first.isdigit():
                    # ref de prefix existente: *1 suffix (no formato explicit)
                    v = declared_p + second
                else:
                    declared_p = first
                    v = first + second
            else:
                v = rest  # raro
        elif " " in line:
            # 2 ou 3 partes
            parts = line.split(" ")
            if len(parts) == 2:
                a, b = parts
                if b.startswith("*"):
                    # <pre> *suffix
                    declared_s = b[1:]
                    v = a + declared_s
                elif a.startswith("*") and a[1:].isdigit():
                    # *1 (ref) + suffix
                    v = declared_p + b
                elif b.startswith("*") and b[1:].isdigit():
                    v = a + declared_s
                else:
                    v = a + b  # fallback
            elif len(parts) == 3:
                p_spec, mid, s_spec = parts
                if p_spec.startswith("*"):
                    p_resolved = p_spec[1:]
                    if p_resolved.isdigit():
                        p_resolved = declared_p
                    else:
                        declared_p = p_resolved
                else:
                    p_resolved = declared_p
                if s_spec.startswith("*"):
                    s_resolved = s_spec[1:]
                    if s_resolved.isdigit():
                        s_resolved = declared_s
                    else:
                        declared_s = s_resolved
                else:
                    s_resolved = declared_s
                v = p_resolved + mid + s_resolved
            else:
                v = line
        else:
            v = line

        out.append(v)
        line_idx_to_value[i] = v
    return out


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

def C1_line_rle_dominante():
    """80% linhas duplicadas."""
    base = ["foo", "bar", "baz", "qux"]
    out = []
    random.seed(42)
    for _ in range(20):
        out.append(random.choice(base))
    return out


def C2_prefix_dominante():
    """80% linhas com prefix forte, 20% excecoes."""
    out = []
    for i in range(16):
        out.append(f"PED-2026-{i:04d}")
    for i in range(4):
        out.append(f"OUTRO-{i}")
    random.seed(42)
    random.shuffle(out)
    return out


def C3_suffix_dominante():
    """80% emails com suffix comum."""
    out = []
    for i in range(16):
        out.append(f"user{i:03d}@gmail.com")
    for i in range(4):
        out.append(f"admin_{i}_other.org")
    random.seed(42)
    random.shuffle(out)
    return out


def C4_misto():
    """50/50 sem dominante claro."""
    out = []
    for i in range(10):
        out.append(f"user{i:03d}@gmail.com")
    for i in range(10):
        out.append(f"abcdefgh{i:02d}xyz")
    random.seed(42)
    random.shuffle(out)
    return out


SCENARIOS = [
    ("C1-line-rle", C1_line_rle_dominante()),
    ("C2-prefix",   C2_prefix_dominante()),
    ("C3-suffix",   C3_suffix_dominante()),
    ("C4-misto",    C4_misto()),
]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main():
    print("=" * 88)
    print("Marcadores deduzidos por recorrencia")
    print("=" * 88)

    all_results = []

    for name, values in SCENARIOS:
        print("\n" + "=" * 88)
        print(f"[{name}] {len(values)} valores")
        print("=" * 88)

        scen = OUT / name
        scen.mkdir(exist_ok=True)

        # Detect mode
        mode, info = detect_dominant_mode(values)

        # Literal
        literal = "\n".join(values) + "\n"
        b_lit = len(literal.encode("utf-8"))
        b_lit_gz = len(gz(literal))
        (scen / "literal.txt").write_text(literal, encoding="utf-8")

        # Explicit
        text_e = encode_explicit(values)
        b_e = len(text_e.encode("utf-8"))
        b_e_gz = len(gz(text_e))
        (scen / "explicit.txt").write_text(text_e, encoding="utf-8")
        try:
            decoded_e = decode_explicit(text_e)
            rt_e = decoded_e == values
        except Exception as ex:
            rt_e = False

        # Deducao
        text_d = encode_deducao(values)
        b_d = len(text_d.encode("utf-8"))
        b_d_gz = len(gz(text_d))
        (scen / "deducao.txt").write_text(text_d, encoding="utf-8")
        try:
            decoded_d = decode_deducao(text_d)
            rt_d = decoded_d == values
        except Exception as ex:
            rt_d = False
            print(f"   decode err: {type(ex).__name__}: {ex}")

        print(f"\n  modo dominante detectado: '{mode}'  cobertura={info}")
        print(f"\n  {'forma':<14} {'bytes':>6} {'+gz':>5} {'vs lit':>9} {'rt':>4}")
        print(f"  {'-'*14} {'-'*6} {'-'*5} {'-'*9} {'-'*4}")
        print(f"  {'literal':<14} {b_lit:>6} {b_lit_gz:>5} {0:>+8.1f}%   - ")
        print(f"  {'explicit':<14} {b_e:>6} {b_e_gz:>5} {(b_e/b_lit-1)*100:>+8.1f}%  {'OK' if rt_e else 'FAIL':>4}")
        print(f"  {'deducao':<14} {b_d:>6} {b_d_gz:>5} {(b_d/b_lit-1)*100:>+8.1f}%  {'OK' if rt_d else 'FAIL':>4}")
        print(f"\n  deducao vs explicit: {(b_d/b_e-1)*100:+.1f}%")

        # Mostra outputs
        print(f"\n  --- explicit (primeiras 8 linhas) ---")
        for line in text_e.splitlines()[:8]:
            print(f"    {line}")
        print(f"  --- deducao (primeiras 8 linhas) ---")
        for line in text_d.splitlines()[:8]:
            print(f"    {line}")

        all_results.append({
            "name": name, "n": len(values),
            "mode_detected": mode,
            "literal": b_lit, "literal_gz": b_lit_gz,
            "explicit": b_e, "explicit_gz": b_e_gz, "rt_explicit": rt_e,
            "deducao": b_d, "deducao_gz": b_d_gz, "rt_deducao": rt_d,
            "deducao_vs_explicit_pct": (b_d/b_e-1)*100,
            "deducao_vs_lit_pct": (b_d/b_lit-1)*100,
        })

    # Sintese
    print("\n" + "=" * 88)
    print("Sintese")
    print("=" * 88)
    print(f"\n  {'cenario':<18} {'modo':>5} {'lit':>5} {'expl':>5} {'dedu':>5} "
          f"{'dedu vs expl':>14} {'dedu vs lit':>13} {'rt-d':>5}")
    print(f"  {'-'*18} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*14} {'-'*13} {'-'*5}")
    for r in all_results:
        rt = "OK" if r["rt_deducao"] else "FAIL"
        print(f"  {r['name']:<18} {r['mode_detected']:>5} {r['literal']:>5} "
              f"{r['explicit']:>5} {r['deducao']:>5} "
              f"{r['deducao_vs_explicit_pct']:>+12.1f}%  "
              f"{r['deducao_vs_lit_pct']:>+11.1f}%  {rt:>5}")

    avg_d_e = sum(r["deducao_vs_explicit_pct"] for r in all_results) / len(all_results)
    avg_d_l = sum(r["deducao_vs_lit_pct"] for r in all_results) / len(all_results)
    print(f"\n  Avg deducao vs explicit: {avg_d_e:+.2f}%")
    print(f"  Avg deducao vs literal:  {avg_d_l:+.2f}%")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
