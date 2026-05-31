"""Lab 25: revisao de markers + RLE adjacente.

Objetivo (interpretado do user):
  1. Clarificar markers: `*` (decl fragmento), `=` (line-ref),
     `_` (lit numerico), `~` (RLE adjacente novo).
  2. Reaplicar RLE adjacente classico (`val~N`) que tinha sido feito
     conceitualmente nos labs 14-15 mas nunca propagado para frente.
  3. Testar 3 variantes do encoder (inline, explicito, hibrido) com RLE.
  4. Comparar nos mesmos 7 cenarios da escala.

3 variantes:
  A — INLINE (lab 18): primeira ocorrencia inline (`*frag` ou literal puro).
                        Idx implicito = numero da linha.
                        SEM encadeamento (`*N=P+ext`).
  B — EXPLICITO (lab 24): header com decls nomeadas (`*N=text`, `*N=P+ext`).
                          PERMITE encadeamento.
  C — HIBRIDO: decide auto. Se ha cadeia ancestral util (>= 2 fragments com
               relacao prefix), usa B. Senao, A.

RLE: detecta runs adjacentes >= 3, append `~N` na primeira ocorrencia.

Sintaxe canonica (proposta v0.5.1):

  | marker  | sintaxe       | significado                              |
  |---------|---------------|------------------------------------------|
  | (none)  | `<text>`      | literal puro                             |
  | `*`     | `*<text>`     | declara fragmento inline (idx = linha)   |
  | `*`+`=` | `*<N>=<text>` | declara fragmento explicito              |
  | `*`+`=` | `*<N>=<P>+<e>`| declara fragmento encadeado              |
  | `=`     | `=<N>`        | refere linha N (line-ref)                |
  | `<N>`   | `<digits>`    | refere idx <N> (so em modo explicito)    |
  | `_`     | `_<text>`     | literal numerico (desambig vs idx)       |
  | `~`     | `<linha>~<N>` | RLE: a linha repete N vezes consecutivas |
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
# PATRICIA (igual lab 24)
# ---------------------------------------------------------------------------

class PatNode:
    __slots__ = ("label", "children", "terminal_lines")
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


def collect_useful(root, min_count=2, min_len=4):
    out = []
    def dfs(n, acc=""):
        full = acc + n.label
        if full and len(full) >= min_len:
            ct = count_terminals(n)
            if ct >= min_count:
                gain = ct * (len(full) - 1) - (len(full) + 2)
                if gain > 0:
                    out.append((full, ct, gain))
        for ch in n.children:
            dfs(ch, full)
    dfs(root)
    out.sort(key=lambda x: -x[2])
    return out


def has_chain_useful(useful_fwd, threshold=2):
    """Retorna True se existem pelo menos `threshold` nos com relacao
    ancestral entre si (= candidato a encadeamento)."""
    fulls = [f for f, _, _ in useful_fwd]
    chained = 0
    for i, fi in enumerate(fulls):
        for j, fj in enumerate(fulls):
            if i != j and fi.startswith(fj) and fi != fj:
                chained += 1
                break
    return chained >= threshold


# ---------------------------------------------------------------------------
# Helpers de RLE adjacente
# ---------------------------------------------------------------------------

def detect_runs(values, min_run=3):
    """Retorna lista de runs (start_idx, run_len, value).

    Runs com run_len < min_run nao sao colapsados — ficam como
    elementos individuais (run_len=1 para cada).
    """
    runs = []
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[j + 1] == values[i]:
            j += 1
        run_len = j - i + 1
        if run_len >= min_run:
            runs.append((i, run_len, values[i]))
        else:
            for k in range(run_len):
                runs.append((i + k, 1, values[i]))
        i = j + 1
    return runs


# ---------------------------------------------------------------------------
# Variante A — INLINE (lab 18 style) + RLE
# ---------------------------------------------------------------------------

def encode_A_inline(values):
    """Inline puro (estilo lab 18): dois espacos de idx separados.
      - Idx de fragmento: contador independente (1, 2, ...) por ordem de
        declaracao `*<text>`. Body emite `<digits>` para referencia.
      - Linha: numero da linha do body. Repeticao de linha INTEIRA usa `=N`.
      - RLE adjacente: `<linha>~N`.
      - Numero literal: `_<digits>` (desambig).
    Sem encadeamento `*N=P+ext` (so na variante B).
    """
    if not values:
        return ""

    fwd = PatNode()
    for i, v in enumerate(values, 1):
        insert(fwd, v, i)
    prefix_cands = collect_useful(fwd)

    rev = PatNode()
    for i, v in enumerate(values, 1):
        insert(rev, v[::-1], i)
    suffix_cands_rev = collect_useful(rev)
    suffix_cands = [(s[::-1], ct, gain) for s, ct, gain in suffix_cands_rev]
    suffix_cands.sort(key=lambda x: -x[2])

    out = []
    line_history = {}     # valor -> num linha do body
    frag_dict = {}        # texto fragmento -> idx fragmento
    next_frag_idx = 1

    runs = detect_runs(values)
    cur_line = 1

    for start_idx, run_len, v in runs:
        if v in line_history:
            base = f"={line_history[v]}"
        else:
            line_history[v] = cur_line
            best_p = ""
            for p, ct, gain in prefix_cands:
                if v.startswith(p):
                    best_p = p
                    break
            rest = v[len(best_p):] if best_p else v
            best_s = ""
            for s, ct, gain in suffix_cands:
                if rest.endswith(s):
                    best_s = s
                    break
            mid = rest[:-len(best_s)] if best_s else rest

            tokens = []
            if best_p:
                if best_p in frag_dict:
                    tokens.append(str(frag_dict[best_p]))
                else:
                    frag_dict[best_p] = next_frag_idx
                    next_frag_idx += 1
                    tokens.append(f"*{best_p}")
            if mid:
                if mid.isdigit():
                    tokens.append(f"_{mid}")
                else:
                    tokens.append(mid)
            if best_s:
                if best_s in frag_dict:
                    tokens.append(str(frag_dict[best_s]))
                else:
                    frag_dict[best_s] = next_frag_idx
                    next_frag_idx += 1
                    tokens.append(f"*{best_s}")
            if not tokens:
                tokens.append(f"_{v}" if v.isdigit() else v)
            base = " ".join(tokens)

        if run_len >= 3:
            out.append(f"{base}~{run_len}")
        else:
            out.append(base)
        cur_line += run_len

    return "\n".join(out) + "\n"


def decode_A(text):
    lines = text.splitlines()
    line_history = [None]   # 1-based: line_history[N] = valor da linha N
    frag_dict = {}          # idx fragmento -> texto
    next_frag_idx = 1
    out = []

    for raw in lines:
        if not raw:
            continue

        # RLE marker
        run_len = 1
        line = raw
        if "~" in line:
            tilde_pos = line.rindex("~")
            tail = line[tilde_pos + 1:]
            if tail.isdigit():
                run_len = int(tail)
                line = line[:tilde_pos]

        # Linha inteira = `=N`?
        if line.startswith("=") and line[1:].isdigit():
            ref = int(line[1:])
            v = line_history[ref]
        else:
            tokens = line.split(" ")
            parts = []
            for tok in tokens:
                if tok.startswith("*"):
                    txt = tok[1:]
                    frag_dict[next_frag_idx] = txt
                    next_frag_idx += 1
                    parts.append(txt)
                elif tok.startswith("_"):
                    parts.append(tok[1:])
                elif tok.isdigit():
                    parts.append(frag_dict[int(tok)])
                else:
                    parts.append(tok)
            v = "".join(parts)

        for _ in range(run_len):
            out.append(v)
            line_history.append(v)

    return out


# ---------------------------------------------------------------------------
# Variante B — EXPLICITO (lab 24 style) + RLE
# ---------------------------------------------------------------------------

def decompose(v, prefix_cands, suffix_cands):
    base = ""
    base_gain = 0
    for p, ct, gain in prefix_cands:
        if v.startswith(p):
            base = p
            base_gain = gain
            break
    best_ext = ""
    best_ext_net = 0
    if base:
        for p, ct, gain in prefix_cands:
            if p == base or not p.startswith(base):
                continue
            if not v.startswith(p):
                continue
            ext = p[len(base):]
            net = ct * (len(ext) - 2) - (7 + len(ext))
            if net > best_ext_net:
                best_ext_net = net
                best_ext = ext
    full_p = base + best_ext
    rest = v[len(full_p):] if full_p else v
    best_s = ""
    best_s_gain = 0
    for s, ct, gain in suffix_cands:
        if rest.endswith(s) and gain > best_s_gain:
            best_s = s
            best_s_gain = gain
    mid = rest[:-len(best_s)] if best_s else rest
    return base, best_ext, mid, best_s


def encode_B_explicit(values):
    if not values:
        return ""

    fwd = PatNode()
    for i, v in enumerate(values, 1):
        insert(fwd, v, i)
    prefix_cands = collect_useful(fwd)
    prefix_info = {full: (ct, gain) for full, ct, gain in prefix_cands}

    rev = PatNode()
    for i, v in enumerate(values, 1):
        insert(rev, v[::-1], i)
    suffix_cands_rev = collect_useful(rev)
    suffix_cands = [(s[::-1], ct, gain) for s, ct, gain in suffix_cands_rev]
    suffix_cands.sort(key=lambda x: -x[2])
    suffix_info = {s: (ct, gain) for s, ct, gain in suffix_cands}

    decompositions = [decompose(v, prefix_cands, suffix_cands) for v in values]

    bases_used = {b for b, _, _, _ in decompositions if b}
    full_ps_used = {(b + e) for b, e, _, _ in decompositions if b and e}
    suffixes_used = {s for _, _, _, s in decompositions if s}

    next_idx = 1
    idx_map = {}

    bases_ordered = sorted(bases_used, key=lambda b: -prefix_info[b][1])
    for b in bases_ordered:
        idx_map[b] = next_idx
        next_idx += 1

    fulls_ordered = sorted(full_ps_used, key=lambda f: -prefix_info[f][1])
    for f in fulls_ordered:
        if f not in idx_map:
            idx_map[f] = next_idx
            next_idx += 1

    suffixes_ordered = sorted(suffixes_used, key=lambda s: -suffix_info[s][1])
    for s in suffixes_ordered:
        if s not in idx_map:
            idx_map[s] = next_idx
            next_idx += 1

    out = []

    # Header
    for b in bases_ordered:
        out.append(f"*{idx_map[b]}={b}")
    for f in fulls_ordered:
        base = ""
        for b in bases_used:
            if f.startswith(b) and len(b) > len(base):
                base = b
        ext = f[len(base):] if base else f
        if base:
            out.append(f"*{idx_map[f]}={idx_map[base]}+{ext}")
        else:
            out.append(f"*{idx_map[f]}={f}")
    for s in suffixes_ordered:
        out.append(f"*{idx_map[s]}={s}")

    # Body com RLE
    line_history = {}
    runs = detect_runs(values)
    # cur_line eh o numero de linha NO BODY (apos header)
    # mas line-ref (=N) refere linha do BODY (1-based dentro do body)
    cur_body_line = 1

    # Mapear i original (line_no global) → cur_body_line
    # Mas vamos simplificar: line_history mapeia value → line global do body
    for start_idx, run_len, v in runs:
        if v in line_history:
            base_line = f"={line_history[v]}"
        else:
            line_history[v] = cur_body_line
            b, e, mid, s = decompositions[start_idx]
            tokens = []
            full_p = b + e
            if full_p:
                tokens.append(str(idx_map[full_p]))
            if mid:
                if mid.isdigit():
                    tokens.append(f"_{mid}")
                else:
                    tokens.append(mid)
            if s:
                tokens.append(str(idx_map[s]))
            if not tokens:
                tokens.append(f"_{v}" if v.isdigit() else v)
            base_line = " ".join(tokens)

        if run_len >= 3:
            out.append(f"{base_line}~{run_len}")
        else:
            out.append(base_line)
        cur_body_line += run_len

    return "\n".join(out) + "\n"


def decode_B(text):
    lines = text.splitlines()
    string_dict = {}
    body_history = []  # 1-based: body_history[N] = valor da linha N do body
    body_history.append(None)
    out = []

    in_header = True
    cur_body_line = 1

    for raw in lines:
        if not raw:
            continue

        # decl
        if raw.startswith("*") and "=" in raw and " " not in raw.split("=", 1)[0]:
            head_until_eq = raw.split("=", 1)[0]
            if head_until_eq[1:].isdigit():
                eq = raw.index("=")
                idx = int(raw[1:eq])
                rhs = raw[eq+1:]
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

        # body
        in_header = False

        # RLE marker
        run_len = 1
        line = raw
        if "~" in line:
            tilde_pos = line.rindex("~")
            tail = line[tilde_pos+1:]
            if tail.isdigit():
                run_len = int(tail)
                line = line[:tilde_pos]

        if line.startswith("="):
            ref = int(line[1:])
            v = body_history[ref]
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

        for _ in range(run_len):
            out.append(v)
            body_history.append(v)
        cur_body_line += run_len

    return out


# ---------------------------------------------------------------------------
# Variante C — HIBRIDO
# ---------------------------------------------------------------------------

def encode_C_hybrid(values):
    """Encoda em ambos os esquemas e escolhe o de menor bytes.
    Robusto: nao depende de heuristica topologica (que pode falhar
    em casos onde candidatos existem mas extensions nao acionam).
    """
    if not values:
        return ""
    text_A = encode_A_inline(values)
    text_B = encode_B_explicit(values)
    if len(text_B.encode("utf-8")) < len(text_A.encode("utf-8")):
        return text_B
    return text_A


def decode_C(text):
    """Detecta se eh A ou B pela presenca de declaracoes em header."""
    # Heuristica: se primeira linha eh `*<digits>=<...>`, eh B
    first = text.split("\n", 1)[0] if text else ""
    if (first.startswith("*") and "=" in first
            and first.split("=", 1)[0][1:].isdigit()):
        return decode_B(text)
    return decode_A(text)


# ---------------------------------------------------------------------------
# Cenarios identicos ao lab 23/24
# ---------------------------------------------------------------------------

def E1_emails_100():
    return [f"user{i:03d}@gmail.com" for i in range(100)]


def E2_emails_1000():
    return [f"user{i:04d}@gmail.com" for i in range(1000)]


def E3_codigos_100():
    return [f"PED-2026-{i:04d}" for i in range(1, 101)]


def E4_codigos_1000():
    return [f"PED-2026-{i:05d}" for i in range(1, 1001)]


def E5_categoricas_100():
    cats = ["red", "blue", "green", "yellow", "purple"]
    random.seed(42)
    return [random.choice(cats) for _ in range(100)]


def E5b_categoricas_runs_100():
    """Cenario novo para EXERCITAR RLE adjacente: categoricas em runs."""
    random.seed(42)
    out = []
    cats = ["red", "blue", "green", "yellow", "purple"]
    for _ in range(20):  # 20 grupos
        cat = random.choice(cats)
        run = random.randint(2, 8)
        out.extend([cat] * run)
    return out[:100]  # limita a 100


def E6_misturado_500():
    random.seed(42)
    out = []
    nomes = ["Ana", "Bruno", "Carlos", "Diana", "Eduardo", "Fernanda"]
    for i in range(500):
        choice = random.choice(["code", "email", "name"])
        if choice == "code":
            out.append(f"INV-2026-{i:05d}")
        elif choice == "email":
            out.append(f"user{i:04d}@gmail.com")
        else:
            out.append(f"{random.choice(nomes)}_{i:03d}")
    return out


def E7_urls_1000():
    base = "https://api.example.com"
    paths = ["users", "orders", "products", "events", "metrics"]
    out = []
    for i in range(1000):
        out.append(f"{base}/v1/{random.choice(paths)}/{i:04d}")
    random.seed(42)
    random.shuffle(out)
    return out


SCENARIOS = [
    ("E1-emails-100",         E1_emails_100()),
    ("E2-emails-1000",        E2_emails_1000()),
    ("E3-codigos-100",        E3_codigos_100()),
    ("E4-codigos-1000",       E4_codigos_1000()),
    ("E5-categoricas-100",    E5_categoricas_100()),
    ("E5b-categoricas-runs",  E5b_categoricas_runs_100()),  # NOVO p/ exercitar RLE
    ("E6-misturado-500",      E6_misturado_500()),
    ("E7-urls-1000",          E7_urls_1000()),
]

LAB23 = {
    "E1-emails-100":         815,
    "E2-emails-1000":       9015,
    "E3-codigos-100":        622,
    "E4-codigos-1000":      7022,
    "E5-categoricas-100":    332,
    "E5b-categoricas-runs":  None,
    "E6-misturado-500":     3858,
    "E7-urls-1000":        14443,
}


def main():
    print("=" * 110)
    print("Lab 25: revisao markers + RLE adjacente — 3 variantes")
    print("=" * 110)

    all_results = []

    for name, values in SCENARIOS:
        print("\n" + "-" * 110)
        print(f"[{name}] {len(values)} valores")
        print("-" * 110)

        scen = OUT / name
        scen.mkdir(exist_ok=True)

        literal = "\n".join(values) + "\n"
        b_lit = len(literal.encode("utf-8"))
        b_lit_gz = len(gz(literal))

        # Variante A — inline
        text_A = encode_A_inline(values)
        b_A = len(text_A.encode("utf-8"))
        try:
            rt_A = decode_A(text_A) == values
        except Exception as e:
            rt_A = False

        # Variante B — explicito
        text_B = encode_B_explicit(values)
        b_B = len(text_B.encode("utf-8"))
        try:
            rt_B = decode_B(text_B) == values
        except Exception as e:
            rt_B = False

        # Variante C — hibrido
        text_C = encode_C_hybrid(values)
        b_C = len(text_C.encode("utf-8"))
        try:
            rt_C = decode_C(text_C) == values
        except Exception as e:
            rt_C = False

        b_C_gz = len(gz(text_C))

        (scen / "A_inline.txt").write_text(text_A[:5000], encoding="utf-8")
        (scen / "B_explicit.txt").write_text(text_B[:5000], encoding="utf-8")
        (scen / "C_hybrid.txt").write_text(text_C[:5000], encoding="utf-8")

        b_lab23 = LAB23[name]
        b_lab23_str = f"{b_lab23:>5}" if b_lab23 else "  n/a"

        sign = lambda x: "+" if x >= 0 else ""
        v_C = (b_C/b_lit-1)*100
        v_C_gz = (b_C_gz/b_lit_gz-1)*100

        print(f"  literal:    {b_lit:>6}B  +gz: {b_lit_gz:>5}")
        print(f"  lab23:      {b_lab23_str}B")
        print(f"  variante A (inline+RLE):    {b_A:>6}B  rt={'OK' if rt_A else 'FAIL'}")
        print(f"  variante B (explicito+RLE): {b_B:>6}B  rt={'OK' if rt_B else 'FAIL'}")
        print(f"  variante C (hibrido+RLE):   {b_C:>6}B  rt={'OK' if rt_C else 'FAIL'}  +gz: {b_C_gz}")
        print(f"  C vs literal:        {sign(v_C)}{v_C:.1f}%")
        print(f"  C+gz vs literal+gz:  {sign(v_C_gz)}{v_C_gz:.1f}%")

        all_results.append({
            "name": name, "n": len(values),
            "literal": b_lit, "literal_gz": b_lit_gz,
            "lab23": b_lab23,
            "A_inline": b_A, "rt_A": rt_A,
            "B_explicit": b_B, "rt_B": rt_B,
            "C_hybrid": b_C, "C_hybrid_gz": b_C_gz, "rt_C": rt_C,
            "C_vs_lit_pct": v_C,
            "C_vs_lit_gz_pct": v_C_gz,
        })

    # Sintese
    print("\n" + "=" * 110)
    print("Sintese — variantes")
    print("=" * 110)
    print(f"\n  {'cenario':<22} {'N':>5} {'lit':>6} {'lab23':>6} "
          f"{'A':>6} {'B':>6} {'C':>6}  {'C vs lit':>9} {'C+gz':>8}  rt(A/B/C)")
    print(f"  {'-'*22} {'-'*5} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6}  {'-'*9} {'-'*8}  ---------")
    for r in all_results:
        l23 = f"{r['lab23']:>6}" if r["lab23"] else "   n/a"
        rts = f"{('OK' if r['rt_A'] else 'FAIL'):>2}/{('OK' if r['rt_B'] else 'FAIL'):>2}/{('OK' if r['rt_C'] else 'FAIL'):>2}"
        print(f"  {r['name']:<22} {r['n']:>5} {r['literal']:>6} {l23} "
              f"{r['A_inline']:>6} {r['B_explicit']:>6} {r['C_hybrid']:>6}  "
              f"{r['C_vs_lit_pct']:>+8.1f}% {r['C_vs_lit_gz_pct']:>+7.1f}%  {rts}")

    avg_C = sum(r["C_vs_lit_pct"] for r in all_results) / len(all_results)
    avg_C_gz = sum(r["C_vs_lit_gz_pct"] for r in all_results) / len(all_results)
    rt_C_ok = sum(1 for r in all_results if r["rt_C"])
    rt_A_ok = sum(1 for r in all_results if r["rt_A"])
    rt_B_ok = sum(1 for r in all_results if r["rt_B"])
    print(f"\n  Avg C vs literal:     {avg_C:+.2f}%")
    print(f"  Avg C+gz vs literal+gz: {avg_C_gz:+.2f}%")
    print(f"  RT: A={rt_A_ok}/{len(all_results)}  B={rt_B_ok}/{len(all_results)}  C={rt_C_ok}/{len(all_results)}")

    (OUT / "results.json").write_text(json.dumps(all_results, indent=2),
                                        encoding="utf-8")


if __name__ == "__main__":
    main()
