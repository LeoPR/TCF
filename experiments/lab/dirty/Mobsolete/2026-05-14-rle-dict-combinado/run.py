"""Lab dirty: RLE de linha + DICT de partes (prefix/suffix/bidir).

4 sintaxes em etapas:
  A. rle-lines  — so RLE de linha inteira (=N)
  B. dict-left  — prefix-DICT + =N
  C. dict-right — suffix-DICT + =N
  D. dict-bidir — prefix + suffix + =N (3 partes por linha)

Cada uma com encoder/decoder separados. Roundtrip validado.

Saida: ./output/<E>/ com 4 sintaxes lado a lado.
"""
from __future__ import annotations
import gzip
import json
import random
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)


def gz(text: str) -> bytes:
    return gzip.compress(text.encode("utf-8"), compresslevel=9)


# ---------------------------------------------------------------------------
# Helpers de detecao
# ---------------------------------------------------------------------------

def lcp(values):
    """Longest common prefix de todos."""
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
    """Longest common suffix."""
    rev = [v[::-1] for v in values]
    return lcp(rev)[::-1]


# ---------------------------------------------------------------------------
# Sintaxe A — rle-lines (so RLE de linha)
# ---------------------------------------------------------------------------

def encode_A(values):
    """Linha repetida vira =N (idx da 1a ocorrencia, 1-based)."""
    out = []
    seen: dict[str, int] = {}
    for i, v in enumerate(values, 1):
        if v in seen:
            out.append(f"={seen[v]}")
        else:
            seen[v] = i
            out.append(v)
    return "\n".join(out) + "\n"


def decode_A(text):
    out = []
    line_idx_to_value: dict[int, str] = {}
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("="):
            ref = int(line[1:])
            v = line_idx_to_value[ref]
            out.append(v)
            line_idx_to_value[i] = v
        else:
            out.append(line)
            line_idx_to_value[i] = line
    return out


# ---------------------------------------------------------------------------
# Sintaxe B — dict-left (prefix + =N)
# ---------------------------------------------------------------------------

def encode_B(values):
    """Header inline: 1a linha declara *prefix; demais usam idx."""
    p = lcp(values)
    if len(p) < 4:
        # Sem prefix util — fallback rle-lines
        return encode_A(values)

    out = []
    seen_lines: dict[str, int] = {}
    declared = False
    for i, v in enumerate(values, 1):
        if v in seen_lines:
            out.append(f"={seen_lines[v]}")
            continue
        seen_lines[v] = i
        if v.startswith(p):
            suffix = v[len(p):]
            if not declared:
                out.append(f"*{p} {suffix}")  # decl inline
                declared = True
            else:
                out.append(f"1 {suffix}")  # idx 1 + suffix
        else:
            # excecao
            out.append(f"\\!{v}")
    return "\n".join(out) + "\n"


def decode_B(text):
    out = []
    line_idx_to_value: dict[int, str] = {}
    prefix = ""
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("="):
            ref = int(line[1:])
            v = line_idx_to_value[ref]
        elif line.startswith("\\!"):
            v = line[2:]
        elif line.startswith("*"):
            # decl inline: *prefix suffix
            rest = line[1:]
            sp = rest.index(" ")
            prefix = rest[:sp]
            suffix = rest[sp+1:]
            v = prefix + suffix
        else:
            # idx + suffix
            sp = line.index(" ")
            idx = int(line[:sp])
            suffix = line[sp+1:]
            if idx == 1:
                v = prefix + suffix
            else:
                raise ValueError(f"unexpected idx {idx}")
        out.append(v)
        line_idx_to_value[i] = v
    return out


# ---------------------------------------------------------------------------
# Sintaxe C — dict-right (suffix + =N)
# ---------------------------------------------------------------------------

def encode_C(values):
    s = lcs(values)
    if len(s) < 4:
        return encode_A(values)

    out = []
    seen_lines: dict[str, int] = {}
    declared = False
    for i, v in enumerate(values, 1):
        if v in seen_lines:
            out.append(f"={seen_lines[v]}")
            continue
        seen_lines[v] = i
        if v.endswith(s):
            prefix_var = v[:-len(s)]
            if not declared:
                out.append(f"{prefix_var} *{s}")
                declared = True
            else:
                out.append(f"{prefix_var} 1")
        else:
            out.append(f"\\!{v}")
    return "\n".join(out) + "\n"


def decode_C(text):
    out = []
    line_idx_to_value: dict[int, str] = {}
    suffix = ""
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("="):
            ref = int(line[1:])
            v = line_idx_to_value[ref]
        elif line.startswith("\\!"):
            v = line[2:]
        else:
            # forma "<prefix-var> *suffix"  ou  "<prefix-var> <idx>"
            sp = line.rindex(" ")
            prefix_var = line[:sp]
            tail = line[sp+1:]
            if tail.startswith("*"):
                suffix = tail[1:]
                v = prefix_var + suffix
            else:
                idx = int(tail)
                if idx == 1:
                    v = prefix_var + suffix
                else:
                    raise ValueError(f"unexpected idx {idx}")
        out.append(v)
        line_idx_to_value[i] = v
    return out


# ---------------------------------------------------------------------------
# Sintaxe D — dict-bidir (prefix + suffix + =N, 3 partes)
# ---------------------------------------------------------------------------

def encode_D(values):
    p = lcp(values)
    s = lcs(values)
    use_prefix = len(p) >= 4
    use_suffix = len(s) >= 4

    if not use_prefix and not use_suffix:
        return encode_A(values)
    if use_prefix and not use_suffix:
        return encode_B(values)
    if use_suffix and not use_prefix:
        return encode_C(values)

    # Bidir: 3 partes por linha
    out = []
    seen_lines: dict[str, int] = {}
    declared_prefix = False
    declared_suffix = False
    for i, v in enumerate(values, 1):
        if v in seen_lines:
            out.append(f"={seen_lines[v]}")
            continue
        seen_lines[v] = i

        has_p = v.startswith(p)
        has_s = v.endswith(s)
        if has_p and has_s:
            mid = v[len(p):]
            mid = mid[:-len(s)] if s else mid
            # Constroi 3 partes
            p_part = "1" if declared_prefix else f"*{p}"
            if not declared_prefix:
                declared_prefix = True
            s_part = "2" if declared_suffix else f"*{s}"
            if not declared_suffix:
                declared_suffix = True
            out.append(f"{p_part} {mid} {s_part}")
        elif has_p:
            mid_plus_suf = v[len(p):]
            p_part = "1" if declared_prefix else f"*{p}"
            if not declared_prefix:
                declared_prefix = True
            out.append(f"{p_part} {mid_plus_suf}")  # 2 partes
        elif has_s:
            pref_plus_mid = v[:-len(s)] if s else v
            s_part = "2" if declared_suffix else f"*{s}"
            if not declared_suffix:
                declared_suffix = True
            out.append(f"{pref_plus_mid} {s_part}")  # 2 partes
        else:
            out.append(f"\\!{v}")
    return "\n".join(out) + "\n"


def decode_D(text):
    out = []
    line_idx_to_value: dict[int, str] = {}
    prefix = None
    suffix = None
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("="):
            ref = int(line[1:])
            v = line_idx_to_value[ref]
        elif line.startswith("\\!"):
            v = line[2:]
        else:
            parts = line.split(" ")
            # Detecta forma:
            #   3 partes: <p-spec> <mid> <s-spec>
            #   2 partes: <p-spec> <mid+s>  ou  <p+mid> <s-spec>
            #   1 parte (raro): so literal
            if len(parts) == 3:
                p_spec, mid, s_spec = parts
                if p_spec.startswith("*"):
                    prefix = p_spec[1:]
                    p_resolved = prefix
                else:
                    p_resolved = prefix
                if s_spec.startswith("*"):
                    suffix = s_spec[1:]
                    s_resolved = suffix
                else:
                    s_resolved = suffix
                v = p_resolved + mid + s_resolved
            elif len(parts) == 2:
                # Decide qual parte eh spec
                a, b = parts
                if a.startswith("*"):
                    prefix = a[1:]
                    v = prefix + b
                elif b.startswith("*"):
                    suffix = b[1:]
                    v = a + suffix
                elif a == "1":
                    v = prefix + b
                elif b == "2":
                    v = a + suffix
                else:
                    # ambiguo — tenta ambas
                    raise ValueError(f"ambiguo: {line!r}")
            else:
                v = line
        out.append(v)
        line_idx_to_value[i] = v
    return out


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

def E1_user_example():
    """5 emails do exemplo literal do user."""
    return [
        "user001@gmail.com",
        "user002@gmail.com",
        "user003@gmail.com",
        "user001@gmail.com",  # repete linha 1
        "user002@hotmail.com",
    ]


def E2_emails_with_dups():
    """50 emails com algumas repeticoes (=N deveria ajudar)."""
    random.seed(42)
    base = [f"user{i:03d}@gmail.com" for i in range(20)]
    base.extend([f"user{i:03d}@yahoo.com" for i in range(20)])
    # Adiciona 10 duplicatas
    for _ in range(10):
        base.append(random.choice(base))
    random.shuffle(base)
    return base


def E3_codigos_sem_dups():
    """30 codigos PED-2026-NNNN (sem duplicatas)."""
    return [f"PED-2026-{i:04d}" for i in range(1, 31)]


def E4_categorical_muitas_dups():
    """20 valores em 4 unicos — muita repeticao."""
    random.seed(42)
    cats = ["red", "blue", "green", "yellow"]
    return [random.choice(cats) for _ in range(20)]


SCENARIOS = [
    ("E1-user-example",         E1_user_example()),
    ("E2-emails-with-dups",     E2_emails_with_dups()),
    ("E3-codigos-sem-dups",     E3_codigos_sem_dups()),
    ("E4-categorical-muitas-dups", E4_categorical_muitas_dups()),
]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

SYNTAXES = [
    ("A-rle-lines",  encode_A, decode_A),
    ("B-dict-left",  encode_B, decode_B),
    ("C-dict-right", encode_C, decode_C),
    ("D-dict-bidir", encode_D, decode_D),
]


def main():
    print("=" * 90)
    print("RLE + DICT combinados (4 sintaxes em etapas)")
    print("=" * 90)

    all_results = []

    for sname, values in SCENARIOS:
        print("\n" + "=" * 90)
        print(f"[{sname}] {len(values)} valores")
        print("=" * 90)

        scen_dir = OUT / sname
        scen_dir.mkdir(exist_ok=True)

        # Literal
        literal = "\n".join(values) + "\n"
        b_lit = len(literal.encode("utf-8"))
        b_lit_gz = len(gz(literal))
        (scen_dir / "literal.txt").write_text(literal, encoding="utf-8")

        print(f"\n  literal: {b_lit}B  +gz: {b_lit_gz}B")
        print(f"\n  {'sintaxe':<14} {'bytes':>6} {'+gz':>5} {'vs lit':>9} {'rt':>4}")
        print(f"  {'-'*14} {'-'*6} {'-'*5} {'-'*9} {'-'*4}")

        scen_results = {"name": sname, "n": len(values),
                          "literal_bytes": b_lit, "literal_gz": b_lit_gz,
                          "syntaxes": {}}

        for syn_name, enc_fn, dec_fn in SYNTAXES:
            try:
                text = enc_fn(values)
                b = len(text.encode("utf-8"))
                b_gz = len(gz(text))
                vs = (b/b_lit - 1)*100
                try:
                    decoded = dec_fn(text)
                    rt = decoded == values
                except Exception as e:
                    rt = False
                rt_str = "OK" if rt else "FAIL"
                sign = "+" if vs >= 0 else ""
                print(f"  {syn_name:<14} {b:>6} {b_gz:>5} "
                      f"{sign}{vs:>+7.1f}% {rt_str:>4}")
                (scen_dir / f"{syn_name}.txt").write_text(text, encoding="utf-8")
                scen_results["syntaxes"][syn_name] = {
                    "bytes": b, "bytes_gz": b_gz,
                    "vs_lit_pct": vs, "roundtrip": rt,
                }
            except Exception as e:
                print(f"  {syn_name:<14} ERRO: {type(e).__name__}: {e}")
                scen_results["syntaxes"][syn_name] = {"error": str(e)}

        # Imprime cada sintaxe (ate 12 linhas)
        for syn_name, _, _ in SYNTAXES:
            text = (scen_dir / f"{syn_name}.txt").read_text(encoding="utf-8")
            print(f"\n  --- {syn_name} ---")
            for line in text.splitlines()[:12]:
                print(f"    {line}")
            if len(text.splitlines()) > 12:
                print(f"    ... ({len(text.splitlines())-12} linhas a mais)")

        all_results.append(scen_results)

    # Sintese
    print("\n" + "=" * 90)
    print("Sintese — bytes por sintaxe x cenario")
    print("=" * 90)
    print(f"\n  {'cenario':<28} {'lit':>5} {'A':>5} {'B':>5} {'C':>5} {'D':>5} {'best':<14}")
    print(f"  {'-'*28} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*14}")
    for r in all_results:
        s = r["syntaxes"]
        all_b = {"lit": r["literal_bytes"]}
        for k, v in s.items():
            if "bytes" in v:
                all_b[k] = v["bytes"]
        best = min(all_b, key=all_b.get)
        print(f"  {r['name']:<28} {r['literal_bytes']:>5} "
              f"{s.get('A-rle-lines',{}).get('bytes','-'):>5} "
              f"{s.get('B-dict-left',{}).get('bytes','-'):>5} "
              f"{s.get('C-dict-right',{}).get('bytes','-'):>5} "
              f"{s.get('D-dict-bidir',{}).get('bytes','-'):>5} "
              f"{best:<14}")

    print("\n  Roundtrip:")
    all_ok = True
    for r in all_results:
        for sn, sv in r["syntaxes"].items():
            if "roundtrip" in sv and not sv["roundtrip"]:
                print(f"    FAIL: {r['name']} / {sn}")
                all_ok = False
    print(f"  {'TUDO OK' if all_ok else 'HA FALHAS'}")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
