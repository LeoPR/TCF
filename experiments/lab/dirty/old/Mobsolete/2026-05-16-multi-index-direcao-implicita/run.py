"""Lab dirty: multi-index com direcao implicita.

Sintaxe auto-descritiva. Decoder deduz tudo pelos marcadores.
Pass 1 (greedy online) implementado; Pass 2 (revisao) adiado.

Tokens:
  *<text>   decl: cria novo idx, valor = <text>
  <n>       ref: idx string n (puro digito)
  _<text>   literal forcado (desambigua "1" como string)
  =<n>      ref linha n
  <text>    literal automatico (declara idx auto se nao existe)

Linha = tokens separados por espaco; concatenacao = valor.

Saida: ./output/
"""
from __future__ import annotations
import gzip
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)


def gz(text):
    return gzip.compress(text.encode("utf-8"), compresslevel=9)


# ---------------------------------------------------------------------------
# Encoder com direcao implicita + multi-index
# ---------------------------------------------------------------------------

def greedy_decompose(v: str, dict_entries: list[str]) -> list[tuple]:
    """Tenta decompor v em (prefix-ref, middle, suffix-ref).

    Retorna lista de tokens: [("ref", idx), ("lit", text), ...] (1-based idx).
    Se nada bate: [("lit", v)].
    """
    if not dict_entries:
        return [("lit", v)]

    # 1. Match exato
    if v in dict_entries:
        idx = dict_entries.index(v) + 1
        return [("ref", idx)]

    # 2. Tenta prefix + suffix simultaneo (escolhe maior cobertura)
    best = None
    for i, p in enumerate(dict_entries):
        if v.startswith(p) and len(p) >= 4:
            for j, s in enumerate(dict_entries):
                if i == j:
                    continue
                if v.endswith(s) and len(s) >= 4:
                    # Garante que prefix e suffix nao se sobrepoem
                    if len(p) + len(s) <= len(v):
                        mid = v[len(p):len(v)-len(s)]
                        cost = 0  # prefere mid menor
                        if best is None or len(mid) < best[2]:
                            best = (i+1, j+1, len(mid), mid)
    if best:
        p_idx, s_idx, _, mid = best
        if mid:
            return [("ref", p_idx), ("lit", mid), ("ref", s_idx)]
        else:
            # Sem middle — eh ref-ref (raro)
            return [("ref", p_idx), ("ref", s_idx)]

    # 3. So prefix
    best_prefix = None
    for i, p in enumerate(dict_entries):
        if v.startswith(p) and len(p) >= 4:
            if best_prefix is None or len(p) > best_prefix[1]:
                best_prefix = (i+1, len(p))
    if best_prefix:
        idx, plen = best_prefix
        rest = v[plen:]
        return [("ref", idx), ("lit", rest)]

    # 4. So suffix
    best_suffix = None
    for i, s in enumerate(dict_entries):
        if v.endswith(s) and len(s) >= 4:
            if best_suffix is None or len(s) > best_suffix[1]:
                best_suffix = (i+1, len(s))
    if best_suffix:
        idx, slen = best_suffix
        pre = v[:-slen]
        return [("lit", pre), ("ref", idx)]

    # 5. Sem padrao — literal
    return [("lit", v)]


def update_dict(dict_entries: list[str], value: str, decomp: list[tuple]):
    """NAO adiciona literais automaticos. So decls explicitas entram no
    dict — necessario para encoder e decoder ficarem em sync."""
    # No-op: dict so cresce via decls explicitas (`*`)
    return


def encode_multi(values: list[str]) -> str:
    """Pass 1 greedy: gera output com tokens marcados."""
    out = []
    string_dict: list[str] = []  # idx 1-based via index+1
    line_history_idx: dict[str, int] = {}  # value -> 1st line idx

    # Pre-populacao: extrair afixos candidatos das primeiras linhas
    # (curto-circuito: olha 2-3 primeiras linhas para semear o dict com
    # prefixes/suffixes comuns)
    sample = values[:min(len(values), 4)]
    if len(sample) >= 2:
        # LCP candidate
        p = sample[0]
        for v in sample[1:]:
            i = 0
            while i < min(len(p), len(v)) and p[i] == v[i]:
                i += 1
            p = p[:i]
            if not p:
                break
        if len(p) >= 4:
            string_dict.append(p)
        # LCS candidate
        rev = [v[::-1] for v in sample]
        rs = rev[0]
        for r in rev[1:]:
            i = 0
            while i < min(len(rs), len(r)) and rs[i] == r[i]:
                i += 1
            rs = rs[:i]
            if not rs:
                break
        s = rs[::-1]
        if len(s) >= 4 and s not in string_dict:
            string_dict.append(s)

    # Tracking de string_dict declarado (para emit `*` na 1a vez)
    declared_set: set[int] = set()  # set de idx ja declarados explicitamente

    for line_no, v in enumerate(values, 1):
        # 1. Linha duplicada?
        if v in line_history_idx:
            out.append(f"={line_history_idx[v]}")
            continue
        line_history_idx[v] = line_no

        # 2. Decompor
        decomp = greedy_decompose(v, string_dict)

        # 3. Atualizar dict (adiciona novos)
        update_dict(string_dict, v, decomp)

        # 4. Emit tokens
        tokens = []
        for kind, payload in decomp:
            if kind == "ref":
                idx = payload
                if idx not in declared_set:
                    # Primeira vez que esse idx eh referenciado:
                    # decl explicita
                    tokens.append(f"*{string_dict[idx-1]}")
                    declared_set.add(idx)
                else:
                    tokens.append(str(idx))
            elif kind == "lit":
                # Literal: se for puro numero, adicionar `_` para
                # desambiguar
                if payload.isdigit():
                    tokens.append(f"_{payload}")
                else:
                    tokens.append(payload)

        out.append(" ".join(tokens))

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------

def decode_multi(text: str) -> list[str]:
    """Decoder unico: deduz tudo pelos marcadores."""
    lines = text.splitlines()
    string_dict: list[str] = []
    line_history: list[str] = []

    out = []
    for line in lines:
        if not line:
            continue
        v = decode_line(line, string_dict, line_history)
        out.append(v)
        line_history.append(v)
    return out


def decode_line(line: str, string_dict: list[str],
                line_history: list[str]) -> str:
    # =N : ref linha
    if line.startswith("="):
        idx = int(line[1:])
        return line_history[idx - 1]

    # Tokens separados por espaco
    tokens = line.split(" ")
    parts = []
    for tok in tokens:
        if tok.startswith("*"):
            # decl: cria novo idx (sempre, mesmo se duplicado)
            text = tok[1:]
            string_dict.append(text)
            parts.append(text)
        elif tok.startswith("_"):
            # literal forcado (desambigua numero)
            parts.append(tok[1:])
        elif tok.isdigit():
            # ref string
            idx = int(tok)
            parts.append(string_dict[idx - 1])
        else:
            # literal automatico — NAO adiciona ao dict
            parts.append(tok)
    return "".join(parts)


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

def C1_user_example():
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


def C2_codigos_uniforme():
    return [f"INV-2026-{i:04d}" for i in range(1, 21)]


def C3_misto_80_20():
    out = [f"INV-2026-{i:04d}" for i in range(16)]
    out.extend([f"OUTRO_{i}" for i in range(4)])
    import random
    random.seed(42)
    random.shuffle(out)
    return out


def C4_emails_2dom():
    out = []
    for i in range(15):
        out.append(f"user{i:03d}@gmail.com")
    for i in range(15):
        out.append(f"user{i+15:03d}@yahoo.com")
    import random
    random.seed(42)
    random.shuffle(out)
    return out


def C5_dups_dominantes():
    base = ["foo", "bar", "baz"]
    import random
    random.seed(42)
    return [random.choice(base) for _ in range(15)]


SCENARIOS = [
    ("C1-user-example", C1_user_example()),
    ("C2-codigos-uniforme", C2_codigos_uniforme()),
    ("C3-misto-80-20", C3_misto_80_20()),
    ("C4-emails-2dom", C4_emails_2dom()),
    ("C5-dups-dominantes", C5_dups_dominantes()),
]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main():
    print("=" * 90)
    print("Multi-index com direcao implicita — Pass 1 greedy")
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

        text_multi = encode_multi(values)
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

        sign = "+" if (b_multi/b_lit-1)*100 >= 0 else ""
        print(f"\n  literal:    {b_lit:>5}B  +gz: {b_lit_gz:>4}")
        print(f"  multi:      {b_multi:>5}B  +gz: {b_multi_gz:>4}  "
              f"({sign}{(b_multi/b_lit-1)*100:+.1f}% vs lit)")
        print(f"  roundtrip: {'OK' if rt else 'FAIL'}")
        if err:
            print(f"  err: {err}")

        # Mostra output
        print(f"\n  --- multi (saida completa) ---")
        for line in text_multi.splitlines():
            print(f"    {line}")

        all_results.append({
            "name": name, "n": len(values),
            "literal": b_lit, "literal_gz": b_lit_gz,
            "multi": b_multi, "multi_gz": b_multi_gz,
            "vs_lit_pct": (b_multi/b_lit-1)*100,
            "roundtrip": rt,
            "err": err,
        })

    # Sintese
    print("\n" + "=" * 90)
    print("Sintese")
    print("=" * 90)
    print(f"\n  {'cenario':<24} {'lit':>5} {'multi':>5} {'vs lit':>9} {'rt':>4}")
    print(f"  {'-'*24} {'-'*5} {'-'*5} {'-'*9} {'-'*4}")
    for r in all_results:
        rt = "OK" if r["roundtrip"] else "FAIL"
        sign = "+" if r["vs_lit_pct"] >= 0 else ""
        print(f"  {r['name']:<24} {r['literal']:>5} {r['multi']:>5} "
              f"{sign}{r['vs_lit_pct']:>+7.1f}% {rt:>4}")

    avg = sum(r["vs_lit_pct"] for r in all_results) / len(all_results)
    print(f"\n  Avg vs literal: {avg:+.2f}%")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
