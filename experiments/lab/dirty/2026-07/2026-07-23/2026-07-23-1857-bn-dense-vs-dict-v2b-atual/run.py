#!/usr/bin/env python3
"""bN-dense base64 vs o encoder ATUAL do TCF (dict/V2-B) — v2 CORRIGIDA pós-verificação.

v1 (obsoleta) reportou "bN vence 8/9, k=2 dá 0.17x, regra: k<=16". A verificação `wf_71934332`
validou o núcleo (comparação total-vs-total é justa; corpo-vs-corpo dá o mesmo; RT real; multi-col
não muda nada — o TCF é colunar) MAS derrubou o enquadramento:
  1. a regra `k<=16` erra fora da janela: em k=17..32 o bN ganharia, e em k>=95 o dict PULA pra
     2 chars/simbolo (base-94 esgota) e o bN ganha de novo. Só era ótima em k in [17,94].
  2. a largura era ESCADA {1,2,4,8} (desperdiça 33% em k=5/6/7); com ceil(log2 k) o quadro muda.
  3. GZIP INVERTE varias colunas (corpo do dict é texto redundante; o do bN é bits densos).
  4. N pequeno mata o ganho — e payload minusculo é foco declarado do projeto.
  5. o separador \\x1f sem escaping CORROMPIA EM SILÊNCIO (corretude, não bytes).

Esta v2 mede os eixos que decidem: gzip, varredura de N, largura EXATA vs escada, cruzamento real
de k (até 256), agregado da TABELA INTEIRA, e escaping seguro. NÃO toca src/tcf. `python run.py`.
"""
from __future__ import annotations

import base64
import csv
import gzip
import math
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
KIT = AQUI.parents[0] / "2026-07-23-1759-bn-lowcard-generaliza-e-compoe"
ROOT = AQUI.parents[5]
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(ROOT / "src"))
import pecas as P  # noqa: E402
from tcf import encode, decode, SideOutputs  # noqa: E402

CSV = Path("Z:/tcf-data/external/adult-census/adult.csv")
OUT = AQUI / "outputs"
OUT.mkdir(exist_ok=True)

N_DEF = 10000
COLS = ["sex", "class", "race", "relationship", "marital-status",
        "workclass", "occupation", "education", "native-country"]


def carregar(n=N_DEF):
    cols = {c: [] for c in COLS}
    with open(CSV, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i >= n:
                break
            for c in COLS:
                cols[c].append(row[c].strip())
    return cols


# ------------------------------------------------------------- largura EXATA (corrige a escada)
def width_bits(k):
    """ceil(log2 k) — largura mínima real. A escada {1,2,4,8} do kit desperdiça até 33%."""
    return max(1, math.ceil(math.log2(k))) if k > 1 else 1


# ------------------------------------------- protótipo com ESCAPING seguro (corrige a corrupção)
SEP = "\x1f"


def _esc(s):
    return s.replace("\\", "\\\\").replace(SEP, "\\u").replace("\n", "\\n")


def _unesc(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            c = s[i + 1]
            out.append("\\" if c == "\\" else SEP if c == "u" else "\n" if c == "n" else c)
            i += 2
        else:
            out.append(s[i]); i += 1
    return "".join(out)


def enc_bn(vals, exact=True):
    """`#PB <w> <n> <domínio escapado>\\n<base64>` — self-contained, com escaping (RT seguro)."""
    domain, runs = P.build_and_scan(P.Fonte(vals))
    k = len(domain)
    w = width_bits(k) if exact else P.width_for(k)
    if w is None:
        return None
    body = base64.b64encode(P.pack_w(P.runs_to_indices(runs), w)).decode("ascii")
    dom = SEP.join(_esc(v) for v in domain)
    return f"#PB {w} {len(vals)} {dom}\n{body}"


def dec_bn(wire):
    head, body = wire.split("\n", 1)
    _mg, w, n, dom = head.split(" ", 3)
    domain = [_unesc(x) for x in dom.split(SEP)]
    return [domain[i] for i in P.unpack_w(base64.b64decode(body), int(w), int(n))]


def b_tcf_col(name, vals):
    so = SideOutputs()
    wire = encode({name: vals}, side_outputs=so)
    pc = (so.per_col or {}).get(name)
    return wire, len(wire.encode()), (getattr(pc, "emitted_mode", None) or "?")


def gz(s):
    return len(gzip.compress(s.encode("utf-8"), 9))


def rodar():
    cols = carregar()
    L = ["# bN-dense vs dict/V2-B ATUAL — v2 CORRIGIDA (pós-verificação wf_71934332)\n",
         "v1 OBSOLETA (regra `k<=16` errada fora da janela; largura em escada; gzip e N não medidos). "
         "Aqui: largura EXATA `ceil(log2 k)`, escaping seguro, **gzip**, **varredura de N**, cruzamento "
         "real de k, e o agregado da TABELA INTEIRA. Comparação total-vs-total self-contained.\n"]

    # ---------- 1. colunas reais: cru E gzip, escada vs exata ----------
    L += ["## 1. Colunas reais (N=10000) — cru e pós-gzip\n",
          "| coluna | k | w escada | w exato | TCF | modo | bN(escada) | bN(exato) | razão exato | "
          "TCF gz | bN gz | razão gz | RT |",
          "|---|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|---:|:---:|"]
    falhas = 0
    inverte_gz = 0
    for c in COLS:
        vals = cols[c]
        wire_t, bt, modo = b_tcf_col(c, vals)
        we, wl = enc_bn(vals, exact=True), enc_bn(vals, exact=False)
        be, bl = len(we.encode()), len(wl.encode())
        rt = (dec_bn(we) == vals) and (dec_bn(wl) == vals) and (decode(wire_t) == {c: vals})
        falhas += (not rt)
        k = len(set(vals))
        gt, gb = gz(wire_t), gz(we)
        if gb > gt:
            inverte_gz += 1
        (OUT / f"{c}.bn-exato.tcfp").write_text(we, encoding="utf-8", newline="")
        L.append(f"| {c} | {k} | {P.width_for(k)} | {width_bits(k)} | {bt} | {modo} | {bl} | {be} | "
                 f"{be/bt:.2f}× | {gt} | {gb} | {gb/gt:.2f}× | {'✅' if rt else '❌'} |")

    # ---------- 2. tabela inteira (o número que faltava) ----------
    wire_full = encode({c: cols[c] for c in COLS})
    b_full = len(wire_full.encode())
    soma_min = sum(min(b_tcf_col(c, cols[c])[1], len(enc_bn(cols[c]).encode())) for c in COLS)
    L += ["\n## 2. Agregado da TABELA INTEIRA (9 colunas, N=10000)\n",
          f"- TCF atual, tabela completa: **{b_full} B**",
          f"- por-coluna `min(TCF, bN-exato)` (o FLOOR proposto): **{soma_min} B** → "
          f"**{soma_min/b_full:.3f}×** ({b_full/soma_min:.2f}× menor)",
          "\nEste é o número honesto de headline — não o 0.17× de uma coluna booleana."]

    # ---------- 3. varredura de N (foco payload minúsculo) ----------
    L += ["\n## 3. Varredura de N — o ganho DESAPARECE em payload pequeno\n",
          "| coluna | N=5 | N=10 | N=20 | N=100 | N=500 | N=2000 | N=10000 |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for c in ("sex", "race"):
        row = [f"| {c} "]
        for n in (5, 10, 20, 100, 500, 2000, 10000):
            v = cols[c][:n]
            bt = b_tcf_col(c, v)[1]
            bn = len(enc_bn(v).encode())
            row.append(f"| {bn/bt:.2f}× ")
        L.append("".join(row) + "|")
    L.append("\n**Crítico**: o ganho é assintótico em N. Em payload minúsculo (foco declarado do "
             "projeto) ele some — o domínio embutido e o header não amortizam.")

    # ---------- 4. cruzamento real de k ----------
    L += ["\n## 4. Cruzamento real de k (sintético uniforme, N=10000)\n",
          "| k | w exato | TCF | modo | bN(exato) | razão |",
          "|---:|---:|---:|:---:|---:|---:|"]
    for k in (2, 4, 8, 16, 17, 32, 64, 94, 95, 128, 256):
        v = [f"c{i%k:03d}" for i in range(10000)]
        bt, modo = b_tcf_col("x", v)[1], b_tcf_col("x", v)[2]
        bn = len(enc_bn(v).encode())
        L.append(f"| {k} | {width_bits(k)} | {bt} | {modo} | {bn} | {bn/bt:.2f}× |")
    L.append("\n**A regra `k<=16` da v1 estava errada**: o dict/V2-B usa base-94, então gasta 1 "
             "char/símbolo só até k=94; a partir de k=95 pula pra 2 chars/símbolo e o bN volta a "
             "ganhar. Não há um limiar simples — por isso a decisão certa é **competir no FLOOR/min**, "
             "não um `if k<=16`.")

    L += ["\n## Conclusão corrigida\n",
          "- **O ganho existe e é real**, mas o headline honesto é o agregado da tabela "
          f"(**{b_full/soma_min:.2f}× menor**), não o 6× de uma coluna booleana em N grande.",
          f"- **gzip inverte {inverte_gz}/9 colunas**: o corpo do dict é texto redundante (gzip come), o "
          "do bN é base64 de bits densos (incompressível). Sob transporte comprimido o ganho encolhe "
          "muito ou vira perda. Pela filosofia do projeto gzip é sinal, não critério — mas ignorá-lo "
          "seria desonesto num formato cujo alvo inclui transmissão.",
          "- **Em payload minúsculo o ganho some** (N=5 ≈ empate) — e esse é o foco declarado. O bN "
          "compensa em coluna GRANDE e cardinalidade baixa.",
          "- **A regra certa NÃO é um limiar de k**: é entrar como **mais um candidato no FLOOR/min** "
          "por coluna, que já é o padrão do TCF — aí é nunca-pior em bytes de wire por construção, "
          "sem depender de acertar limiar nenhum.",
          "- **Largura exata importa**: `ceil(log2 k)` em vez da escada {1,2,4,8} recupera até 33% "
          "(k=5/6/7) — é o 'mecanismo lógico bom' antes de qualquer otimização fina.",
          f"\n**9 colunas + varreduras · {falhas} falhas de RT.** Regenera: `python run.py`."]

    (AQUI / "result.md").write_text("\n".join(L), encoding="utf-8", newline="\n")
    print(f"OK · {falhas} falhas de RT · gzip inverte {inverte_gz}/9 · tabela {b_full/soma_min:.2f}x menor")
    return falhas


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)
