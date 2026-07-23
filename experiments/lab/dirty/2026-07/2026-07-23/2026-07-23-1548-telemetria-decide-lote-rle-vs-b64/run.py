#!/usr/bin/env python3
"""Micro-lab — a TELEMETRIA (custos contados de qualquer forma) decide o modo POR LOTE?

Reformulação do owner (2026-07-23): os vetores (memória/cpu/latência) já existem; o que muda é a
FORMA como o TCF compõe o arquivo. Hoje o pipeline JÁ escolhe o modo vencedor POR COLUNA
(`emitted_mode` ∈ tcf/raw/dict/split) a partir de bytes "contados no processo, não no fim"
(src/tcf/side_outputs.py:62-67 — zero passada extra). Hipótese: a MESMA telemetria pode decidir POR
LOTE dentro de uma coluna bool — quais lotes viram RLE e quais viram base64 — e lotes independentes
são o que permite liberar/paralelizar por estágio.

MEDIÇÃO JUSTA (corpo-vs-corpo): o `#PB.b S manif n\\n` (magic+S+n) é framing GENÉRICO que QUALQUER
composição pagaria; comparar o corpo do batch-dyn (que inclui o manifesto `RDDR`, custo intrínseco
da decisão por lote) contra o corpo do modo único. Assim isola a COMPOSIÇÃO do framing.

O que MEDE (bool heterogêneo, dados pequenos, viabilidade): por lote, telemetria = run-count (do
scan) + tamanho -> fórmula de custo (denso=b64_len; rle=soma sobre runs); cada lote pega seu modo;
compara CORPOS: whole-dense / whole-rle / whole-best / batch-dyn(S). RT self-contained + passe único.
NÃO toca src/tcf. `python run.py`.
"""
from __future__ import annotations

import base64
import json
import math
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[5]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode  # noqa: E402

INP, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (INP, OUT):
    d.mkdir(exist_ok=True)


class Fonte:
    def __init__(self, bits):
        self._bits, self.reads = bits, 0

    def __len__(self):
        return len(self._bits)

    def __getitem__(self, i):
        self.reads += 1
        return self._bits[i]


def scan_runs(seq, lo, hi):
    """UM passe sobre seq[lo:hi] -> [(val,len)]. Cada índice lido 1 vez (guarda o lookahead)."""
    runs = []
    if hi <= lo:
        return runs
    cur, L = seq[lo], 1
    for i in range(lo + 1, hi):
        x = seq[i]
        if x == cur:
            L += 1
        else:
            runs.append((1 if cur else 0, L))
            cur, L = x, 1
    runs.append((1 if cur else 0, L))
    return runs


def b64_len(nbits):
    return math.ceil(math.ceil(nbits / 8) / 3) * 4


def size_dense(nelems):
    return b64_len(nelems)


def size_rle(runs):
    return 1 + 1 + sum(len(str(L)) for _, L in runs) + (len(runs) - 1)


def _pack(bits):
    s = "".join("1" if b else "0" for b in bits)
    s += "0" * ((-len(s)) % 8)
    return bytes(int(s[i:i + 8], 2) for i in range(0, len(s), 8))


def _unpack(data, n):
    ab = "".join(format(b, "08b") for b in data)
    return [ab[i] == "1" for i in range(n)]


def enc_dense(bits):
    return base64.b64encode(_pack(bits)).decode("ascii")


def dec_dense(w, n):
    return _unpack(base64.b64decode(w), n)


def enc_rle_runs(runs):
    return f"{runs[0][0]}:" + ",".join(str(L) for _, L in runs)


def dec_rle(w):
    start, rest = w.split(":", 1)
    v, out = (start == "1"), []
    for L in rest.split(","):
        out.extend([v] * int(L))
        v = not v
    return out


def runs_to_bits(runs):
    out = []
    for v, L in runs:
        out.extend([v == 1] * L)
    return out


# ------------------------------------------------------ composições -> retorna (corpo, RT-decoder)
def body_whole_dense(bits):
    return enc_dense(bits)


def body_whole_rle(bits):
    return enc_rle_runs(scan_runs(bits, 0, len(bits)))


def batch_dyn(fonte, S):
    """Fatia em lotes de S; cada lote decide o modo pela TELEMETRIA. Retorna (corpo, manifesto).
    CORPO = manifesto + ';'.join(bodies). UM passe (scan por lote soma == n)."""
    n = len(fonte)
    manif, bodies = [], []
    for lo in range(0, n, S):
        hi = min(lo + S, n)
        runs = scan_runs(fonte, lo, hi)                # telemetria do lote (passe único)
        if size_rle(runs) < size_dense(hi - lo):       # decisão = SÓ os números
            manif.append("R")
            bodies.append(enc_rle_runs(runs))
        else:
            manif.append("D")
            bodies.append(enc_dense(runs_to_bits(runs)))
    manif = "".join(manif)
    return manif + "\n" + ";".join(bodies), manif      # corpo = manifesto + bodies


def dec_batch_dyn(corpo, S, n):
    manif, body = corpo.split("\n", 1)
    parts = body.split(";") if body else []
    out = []
    for i, seg in enumerate(parts):
        if manif[i] == "R":
            out.extend(dec_rle(seg))
        else:
            out.extend(dec_dense(seg, min(S, n - i * S)))
    return out


def _lcg(n, pct, seed):
    s, out = seed, []
    for _ in range(n):
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        out.append((s % 100) < pct)
    return out


def datasets():
    blocky = []
    for k in range(4):
        blocky += [True] * 32 + _lcg(32, 50, 100 + k)          # run|ruído × 4  (n=256)
    blocky_big = []
    for k in range(8):
        blocky_big += [True] * 128 + _lcg(128, 50, 200 + k)    # run|ruído × 8  (n=2048)
    return {
        "blocky":     blocky,                                   # heterogêneo pequeno
        "blocky-big": blocky_big,                               # heterogêneo, n grande (amortiza)
        "half-half":  [True] * 128 + _lcg(128, 50, 7),          # metade run, metade ruído
        "runny":      _lcg(256, 6, 3),                           # quase tudo run -> whole-rle
        "noisy":      _lcg(256, 50, 9),                          # tudo ruído -> whole-dense
        "alt":        [bool(i % 2) for i in range(256)],        # alternado -> whole-dense
    }


def rodar():
    casos = datasets()
    SIZES = [32, 64, 128]
    linhas = ["# Telemetria decide o modo POR LOTE (RLE vs base64) — CORPO-vs-corpo\n",
              "Bool heterogêneo, dados pequenos. Compara o CORPO de cada composição (o framing genérico "
              "magic+S+n é igual pra todas e fica de fora; o manifesto `RDDR` É custo do batch-dyn). "
              "`whole-*`=1 modo/coluna; `batch-dyn/S`=modo por lote pela telemetria. `reads/n` 1.0=passe "
              "único; RT self-contained.\n",
              "| caso | n | whole-dense | whole-rle | whole-best | bd/32 | bd/64 | bd/128 | melhor corpo | Δ vs best | reads/n | RT |",
              "|---|---:|---:|---:|---:|---:|---:|---:|:---:|---:|:---:|:---:|"]
    falhas = 0
    for nome, bits in casos.items():
        (INP / f"{nome}.json").write_text(json.dumps(bits), encoding="utf-8")
        n = len(bits)
        json_rt = json.loads(json.dumps(bits))

        wd = len(body_whole_dense(bits))
        wr = len(body_whole_rle(bits))
        wbest = min(wd, wr)

        bd, rt_all, reads_one = {}, True, True
        for S in SIZES:
            fonte = Fonte(bits)
            corpo, manif = batch_dyn(fonte, S)
            back = dec_batch_dyn(corpo, S, n)
            rt_all &= (back == bits == json_rt)
            reads_one &= (fonte.reads == n)
            bd[S] = len(corpo)
            (OUT / f"{nome}.bd{S}.tcfp").write_text(corpo, encoding="utf-8", newline="")

        cand = {"whole-dense": wd, "whole-rle": wr,
                "bd/32": bd[32], "bd/64": bd[64], "bd/128": bd[128]}
        melhor = min(cand, key=cand.get)
        best_bd = min(bd.values())
        delta = best_bd - wbest                          # <0 = batch-dyn ganha do melhor modo único
        ok = rt_all and reads_one
        falhas += (not ok)
        linhas.append(
            f"| {nome} | {n} | {wd} | {wr} | {wbest} | {bd[32]} | {bd[64]} | {bd[128]} | {melhor} | "
            f"{delta:+d} | {'1.0' if reads_one else '>1'} | {'✅' if rt_all else '❌'} |")

    linhas.append("\n## Leitura (telemetria por lote + composição)\n")
    linhas.append("- **Medição justa (corpo)**: o framing genérico é o mesmo pra todos; o que se compara "
                  "é a COMPOSIÇÃO. `Δ vs best` < 0 = o dinâmico-por-lote bate o melhor modo único.")
    linhas.append("- **A telemetria já resolve a decisão**: por lote, denso=`b64_len(S)` (fórmula grátis) "
                  "e rle=soma sobre os runs do lote (do scan que você já faz) — os mesmos números que o "
                  "pipeline conta 'no processo, não no fim' (emitted_bytes/mode, side_outputs.py:62-67), "
                  "só que por LOTE. Materializa só o vencedor.")
    linhas.append("- **Passe único preservado**: `reads/n==1.0` mesmo fatiando (fatias disjuntas).")
    linhas.append("- **Onde ganha vs onde o overhead do manifesto pesa**: ver `Δ` e o `S` vencedor por "
                  "caso — heterogêneo grande favorece o dinâmico; homogêneo/pequeno favorece modo único "
                  "(manifesto por lote não se paga). A GRANULARIDADE (S, e lote-vs-coluna) é mais um "
                  "número que a telemetria escolhe — não um valor fixo.")
    linhas.append("- **Composição = a alavanca / paralelismo**: o manifesto `RDDR...` É a forma do arquivo "
                  "mudando por lote; lotes são unidades INDEPENDENTES (encoda/decoda sozinhas) — base pra "
                  "liberar/paralelizar por estágio. Trade explícito: fixo=paralelizável mas paga fronteira; "
                  "adaptativo (fronteira só na virada de regime, como o seq-RLE) comprime mais mas é menos "
                  "paralelizável. A telemetria informa os dois lados.")
    linhas.append(f"\n**{len(casos)} casos × {len(SIZES)} lotes · {falhas} falhas (RT + passe único).** "
                  "Regenera: `python run.py`.")
    (AQUI / "result.md").write_text("\n".join(linhas), encoding="utf-8", newline="\n")
    print(f"OK · {len(casos)} casos · {falhas} falhas (RT + passe unico por lote)")
    return falhas


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)
