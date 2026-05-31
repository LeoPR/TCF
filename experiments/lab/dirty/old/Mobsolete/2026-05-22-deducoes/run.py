"""Lab 22: deduções para espremer mais bytes.

3 deduções:
  D1 — idx por contagem: omitir `_` quando idx ainda nao foi declarado
        (numero solto = literal, nao ref)
  D2 — alfabeto a-z para idx: idx 1..26 -> a..z (1 char, sem aumentar
        para 2 quando passa de 9)
  D3 — `=` redundante: omitir em modos onde so ha line-rle

Compara com lab 21 base.

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
# Encoder simples (lab 16/19 base) com 3 deducoes opcionais
# ---------------------------------------------------------------------------

def lcp_str(a, b):
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return i


def lcs_str(values):
    if not values:
        return ""
    rev = [v[::-1] for v in values]
    p = rev[0]
    for v in rev[1:]:
        i = 0
        while i < min(len(p), len(v)) and p[i] == v[i]:
            i += 1
        p = p[:i]
        if not p:
            break
    return p[::-1]


def lcp_full(values):
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


# Alfabeto adaptativo: idx 1..26 = a..z, 27..52 = A..Z, depois 0..9, depois decimal
_ALPHA = "abcdefghijklmnopqrstuvwxyz"
_ALPHA_UP = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def idx_to_alpha(idx: int) -> str:
    """Converte 1-based idx para alfabeto compacto (1 char preferencial)."""
    if 1 <= idx <= 26:
        return _ALPHA[idx - 1]
    if 27 <= idx <= 52:
        return _ALPHA_UP[idx - 27]
    return str(idx)  # 53+ vira decimal multidigito


def alpha_to_idx(s: str) -> int:
    """Inverso de idx_to_alpha."""
    if len(s) == 1:
        c = s[0]
        if c in _ALPHA:
            return _ALPHA.index(c) + 1
        if c in _ALPHA_UP:
            return _ALPHA_UP.index(c) + 27
    if s.isdigit():
        return int(s)
    raise ValueError(f"cannot decode idx token: {s!r}")


def is_idx_token(tok: str) -> bool:
    """Detecta se tok eh um idx (alpha ou digit)."""
    if not tok:
        return False
    if len(tok) == 1 and (tok in _ALPHA or tok in _ALPHA_UP):
        return True
    return tok.isdigit()


# ---------------------------------------------------------------------------
# Encoder com deducoes opcionais
# ---------------------------------------------------------------------------

def encode(values, *, dedu_count=False, dedu_alpha=False, dedu_eq=False):
    if not values:
        return ""

    # Detect afixos
    p = lcp_full(values)
    s = lcs_str(values)
    use_p = len(p) >= 4
    use_s = len(s) >= 4 and (not use_p or len(p) + len(s) < min(len(v) for v in values))

    declared: dict[str, int] = {}
    line_history: dict[str, int] = {}

    out = []

    # Detecta se ha string-idx refs (para D3)
    has_string_idx_refs = use_p or use_s

    omit_eq = dedu_eq and not has_string_idx_refs

    for line_no, v in enumerate(values, 1):
        if v in line_history:
            ref = line_history[v]
            if omit_eq:
                out.append(str(ref) if not dedu_alpha else idx_to_alpha(ref))
            else:
                out.append(f"={ref}")
            continue
        line_history[v] = line_no

        # Decompoe
        best_p = p if use_p and v.startswith(p) else ""
        best_s = s if use_s and v.endswith(s) and len(v) > len(best_p) + len(s) else ""
        mid = v
        if best_p:
            mid = mid[len(best_p):]
        if best_s and len(mid) >= len(best_s):
            mid = mid[:-len(best_s)]

        tokens = []

        def emit_idx(text, kind):
            if text in declared:
                idx = declared[text]
                if dedu_alpha:
                    tokens.append(idx_to_alpha(idx))
                else:
                    tokens.append(str(idx))
            else:
                idx = len(declared) + 1
                declared[text] = idx
                tokens.append(f"*{text}")

        if best_p:
            emit_idx(best_p, "prefix")
        if mid:
            # D1 — dedu_count: se idx ainda nao foi declarado E nao eh
            # texto que parece numero, dispense `_`
            # Mas se mid eh puro digito, sempre precisa _ para nao confundir
            if mid.isdigit():
                if dedu_count and len(declared) == 0:
                    # Nenhum idx declarado: numero nao pode ser ref
                    tokens.append(mid)
                else:
                    tokens.append(f"_{mid}")
            else:
                tokens.append(mid)
        if best_s:
            emit_idx(best_s, "suffix")

        if not tokens:
            tokens.append(f"_{v}" if v.isdigit() else v)

        out.append(" ".join(tokens))

    if omit_eq:
        out = ["#mode:lineRle"] + out

    return "\n".join(out) + "\n"


def decode(text, *, dedu_count=False, dedu_alpha=False):
    lines = text.splitlines()
    if not lines:
        return []

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
        elif mode == "lineRle" and len(line.split()) == 1:
            tok = line.strip()
            if dedu_alpha and len(tok) == 1 and (tok in _ALPHA or tok in _ALPHA_UP):
                ref = alpha_to_idx(tok)
            elif tok.isdigit():
                ref = int(tok)
            else:
                # so 1 token nao numerico — eh literal puro
                v = tok
                out.append(v)
                line_history.append(v)
                continue
            v = line_history[ref - 1]
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
                elif dedu_alpha and len(tok) == 1 and (tok in _ALPHA or tok in _ALPHA_UP):
                    idx = alpha_to_idx(tok)
                    parts.append(string_dict[idx - 1])
                elif tok.isdigit():
                    if dedu_count and int(tok) > len(string_dict):
                        # numero nao eh idx valido — eh literal
                        parts.append(tok)
                    else:
                        parts.append(string_dict[int(tok) - 1])
                else:
                    parts.append(tok)
            v = "".join(parts)

        out.append(v)
        line_history.append(v)

    return out


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

def C1_emails():
    return [
        "user001@gmail.com", "user002@gmail.com",
        "user003@gmail.com", "user004@gmail.com",
        "user005@gmail.com", "user006@gmail.com",
        "user007@gmail.com", "user008@gmail.com",
        "user009@gmail.com", "user010@gmail.com",
    ]


def C2_codigos():
    return [f"INV-2026-{i:04d}" for i in range(1, 21)]


def C3_dups_dominantes():
    base = ["foo", "bar", "baz", "qux"]
    random.seed(42)
    return [random.choice(base) for _ in range(20)]


def C4_emails_dominio_unico():
    return [f"user{i:03d}@domain.com" for i in range(20)]


def C5_30_idx():
    """Forca uso de >9 idx para testar alfabeto."""
    return [f"PROD-{c}-2026" for c in "abcdefghijklmnopqrstuvwxyz"]  # 26 unicos


SCENARIOS = [
    ("C1-emails-10", C1_emails()),
    ("C2-codigos", C2_codigos()),
    ("C3-dups", C3_dups_dominantes()),
    ("C4-emails-dom-unico", C4_emails_dominio_unico()),
    ("C5-26-idx", C5_30_idx()),
]


def main():
    print("=" * 92)
    print("Lab 22: deduções (D1=count, D2=alfabeto, D3=eq)")
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

        # Variantes
        variants = [
            ("base",       dict()),
            ("D1-count",   dict(dedu_count=True)),
            ("D2-alpha",   dict(dedu_alpha=True)),
            ("D3-eq",      dict(dedu_eq=True)),
            ("D-all",      dict(dedu_count=True, dedu_alpha=True, dedu_eq=True)),
        ]

        print(f"\n  literal: {b_lit}B  +gz: {b_lit_gz}")
        print(f"\n  {'variant':<12} {'bytes':>6} {'+gz':>5} {'vs lit':>9} {'rt':>4}")
        print(f"  {'-'*12} {'-'*6} {'-'*5} {'-'*9} {'-'*4}")

        scen_results = {"name": name, "n": len(values),
                          "literal": b_lit, "literal_gz": b_lit_gz,
                          "variants": {}}

        for vname, kwargs in variants:
            text = encode(values, **kwargs)
            b = len(text.encode("utf-8"))
            b_gz = len(gz(text))
            try:
                # decoder usa as mesmas flags
                dec = decode(text,
                              dedu_count=kwargs.get("dedu_count", False),
                              dedu_alpha=kwargs.get("dedu_alpha", False))
                rt = dec == values
            except Exception as e:
                rt = False
            sign = "+" if (b/b_lit-1)*100 >= 0 else ""
            rt_str = "OK" if rt else "FAIL"
            print(f"  {vname:<12} {b:>6} {b_gz:>5} {sign}{(b/b_lit-1)*100:>+7.1f}% {rt_str:>4}")
            (scen / f"{vname}.txt").write_text(text, encoding="utf-8")
            scen_results["variants"][vname] = {
                "bytes": b, "bytes_gz": b_gz,
                "vs_lit_pct": (b/b_lit-1)*100,
                "roundtrip": rt,
            }

        # Mostra D-all
        print(f"\n  --- D-all output ---")
        text_all = encode(values, dedu_count=True, dedu_alpha=True, dedu_eq=True)
        for line in text_all.splitlines()[:10]:
            print(f"    {line}")
        if len(text_all.splitlines()) > 10:
            print(f"    ... ({len(text_all.splitlines())-10} a mais)")

        all_results.append(scen_results)

    # Sintese
    print("\n" + "=" * 92)
    print("Sintese — efeito das deduções")
    print("=" * 92)
    print(f"\n  {'cenario':<22} {'lit':>5} {'base':>5} {'D-all':>6} "
          f"{'D-all vs base':>14}")
    print(f"  {'-'*22} {'-'*5} {'-'*5} {'-'*6} {'-'*14}")
    for r in all_results:
        b_base = r["variants"]["base"]["bytes"]
        b_all = r["variants"]["D-all"]["bytes"]
        diff = (b_all/b_base - 1) * 100 if b_base else 0
        sign = "+" if diff >= 0 else ""
        print(f"  {r['name']:<22} {r['literal']:>5} {b_base:>5} {b_all:>6} "
              f"{sign}{diff:>+12.1f}%")

    avg = sum((r["variants"]["D-all"]["bytes"]/r["variants"]["base"]["bytes"]-1)*100
              for r in all_results) / len(all_results)
    print(f"\n  Avg D-all vs base: {avg:+.2f}%")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
