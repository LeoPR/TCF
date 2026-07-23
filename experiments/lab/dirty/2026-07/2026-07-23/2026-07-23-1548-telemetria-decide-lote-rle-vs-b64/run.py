#!/usr/bin/env python3
"""Micro-lab — telemetria decide modo por lote: FIXO-S (frágil) vs ADAPTATIVO (robusto).

CORRIGIDO após verificação adversarial (wf_876541f7, 2026-07-23). A v1 reportou ganho -23%/-25% do
batch de tamanho FIXO — mas isso era ARTEFATO DE ALINHAMENTO: os blocos dos dados tinham tamanho
== S vencedor (128). Com blocos DESALINHADOS o batch-fixo PERDE (a verificação mediu +8 a +54), e a
perda supera o ganho alinhado. Esta versão MEDE o desalinhado (registra a perda) e acrescenta a
SEGMENTAÇÃO ADAPTATIVA (fronteira na virada de regime, não em S fixo — alignment-free).

Também corrige o enquadramento: o que é "custo de qualquer forma" é SÓ o run-list da coluna (o
`_rle_adjacente` já roda sobre o bool e emite `*N|`). A segmentação-por-lote e o TAMANHO base64 são
computação NOVA (barata), não reuso — o pipeline nunca calcula bitmap base64. E `emitted_mode` é do
`.8M` multi-col; o caminho `.8H` do bool single-col não tem ponto de seleção. (grounding wf_876541f7)

Composições comparadas (corpo-vs-corpo; framing genérico fora):
  whole-dense / whole-rle / whole-best(min)  — 1 modo pra coluna
  batch-fix/S  — modo por LOTE de tamanho fixo S (frágil a alinhamento)
  seg-adapt    — segmentos com FRONTEIRA na virada de regime, do run-list (alignment-free)
RT self-contained-do-corpo p/ seg-adapt (cada segmento declara seu count); batch-fix precisa de S,n.
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
from tcf import encode  # noqa: E402  (baseline de referência)

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


# --------------------------------------------------- COMPOSIÇÃO A: batch de tamanho FIXO (frágil)
def batch_fix(fonte, S):
    n = len(fonte)
    manif, bodies = [], []
    for lo in range(0, n, S):
        hi = min(lo + S, n)
        runs = scan_runs(fonte, lo, hi)
        if size_rle(runs) < b64_len(hi - lo):
            manif.append("R"); bodies.append(enc_rle_runs(runs))
        else:
            manif.append("D"); bodies.append(enc_dense(runs_to_bits(runs)))
    return "".join(manif) + "\n" + ";".join(bodies), "".join(manif)


def dec_batch_fix(corpo, S, n):
    manif, body = corpo.split("\n", 1)
    parts = body.split(";") if body else []
    out = []
    for i, seg in enumerate(parts):
        out.extend(dec_rle(seg) if manif[i] == "R" else dec_dense(seg, min(S, n - i * S)))
    return out


# ------------------------------------- COMPOSIÇÃO B: segmentação ADAPTATIVA (fronteira no regime)
def seg_adapt(fonte):
    """UM scan da coluna -> segmentos com fronteira ONDE o modo vira (greedy, 1 acumulador).
    Cada segmento declara seu count -> corpo AUTO-DECODÁVEL (não precisa de S nem n externos)."""
    runs = scan_runs(fonte, 0, len(fonte))
    segs, aberto = [], []
    for v, L in runs:
        open_bits = sum(rl for _, rl in aberto)
        simbolico = 1 + len(str(L)) + 1 + 1                 # "R"+len+":"+val
        marginal_d = b64_len(open_bits + L) - b64_len(open_bits)
        if simbolico < marginal_d:                          # o run paga o marcador -> extrai
            if aberto:
                segs.append(_emit_D(aberto)); aberto = []
            segs.append(f"R{L}:{v}")
        else:
            aberto.append((v, L))
    if aberto:
        segs.append(_emit_D(aberto))
    return ";".join(segs)


def _emit_D(runs_acc):
    bits = runs_to_bits(runs_acc)
    return f"D{len(bits)}:{enc_dense(bits)}"


def dec_seg_adapt(corpo):
    out = []
    for seg in corpo.split(";"):
        head, payload = seg[0], seg[1:]
        if head == "R":
            L, v = payload.split(":")
            out.extend([v == "1"] * int(L))
        else:
            count, b64 = payload.split(":")
            out.extend(dec_dense(b64, int(count)))
    return out


# --------------------------------------------------------------------------------- datasets
def _lcg(n, pct, seed):
    s, out = seed, []
    for _ in range(n):
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        out.append((s % 100) < pct)
    return out


def _blocos(run_len, noise_len, reps, seed0):
    out = []
    for k in range(reps):
        out += [True] * run_len + _lcg(noise_len, 50, seed0 + k)
    return out


def datasets():
    return {
        # HETEROGÊNEO — bloco ALINHADO a S=128 (favorece batch-fix; teto do ganho fixo)
        "het-align128": _blocos(128, 128, 8, 200),          # n=2048, blocos de 128
        # HETEROGÊNEO — bloco DESALINHADO de qualquer S∈{32,64,128} (caso realista)
        "het-mis100":   _blocos(100, 100, 10, 300),         # n=2000, blocos de 100
        "het-mis77":    _blocos(77, 51, 15, 400),           # n=1920, blocos de 77/51
        "half-100-156": [True] * 100 + _lcg(156, 50, 7),    # n=256, fronteira em 100 (flip do -11)
        # HOMOGÊNEO — controle (nenhuma composição por-lote deve ganhar)
        "noisy":        _lcg(2048, 50, 9),
        "alt":          [bool(i % 2) for i in range(2048)],
    }


def rodar():
    casos = datasets()
    SIZES = [32, 64, 128]
    linhas = ["# Telemetria decide modo por lote: FIXO-S (frágil) vs ADAPTATIVO (robusto)\n",
              "Corrigido pós-verificação (wf_876541f7). Corpo-vs-corpo. `batch-fix` = lote de S fixo; "
              "`seg-adapt` = fronteira na virada de regime (do run-list, sem S). `Δfix`/`Δadapt` = corpo "
              "− whole-best (<0 ganha do melhor modo único). `align?` = bloco casa algum S. RT + passe único.\n",
              "| caso | n | whole-best | batch-fix(melhor S) | Δfix | seg-adapt | Δadapt | reads/n | RT |",
              "|---|---:|---:|---:|---:|---:|---:|:---:|:---:|"]
    falhas = 0
    for nome, bits in casos.items():
        (INP / f"{nome}.json").write_text(json.dumps(bits), encoding="utf-8")
        n = len(bits)
        json_rt = json.loads(json.dumps(bits))

        wd = len(enc_dense(bits))
        wr = len(enc_rle_runs(scan_runs(bits, 0, n)))
        wbest = min(wd, wr)

        # batch-fix: melhor S (um oráculo pró-fix — mesmo assim perde no desalinhado)
        bf, rt_all, reads_one = {}, True, True
        for S in SIZES:
            fonte = Fonte(bits)
            corpo, _ = batch_fix(fonte, S)
            rt_all &= (dec_batch_fix(corpo, S, n) == bits == json_rt)
            reads_one &= (fonte.reads == n)
            bf[S] = len(corpo)
        best_fix = min(bf.values())

        # seg-adapt
        fonte = Fonte(bits)
        corpo_a = seg_adapt(fonte)
        rt_all &= (dec_seg_adapt(corpo_a) == bits == json_rt)
        reads_one &= (fonte.reads == n)
        adapt = len(corpo_a)
        (OUT / f"{nome}.seg-adapt.tcfp").write_text(corpo_a, encoding="utf-8", newline="")

        ok = rt_all and reads_one
        falhas += (not ok)
        linhas.append(
            f"| {nome} | {n} | {wbest} | {best_fix} | {best_fix - wbest:+d} | {adapt} | "
            f"{adapt - wbest:+d} | {'1.0' if reads_one else '>1'} | {'✅' if rt_all else '❌'} |")

    linhas.append("\n## Leitura corrigida\n")
    linhas.append("- **Batch de S FIXO é frágil a alinhamento**: ganha só quando a fronteira de regime "
                  "cai em múltiplo de S (`het-align128`, Δfix<0); em blocos desalinhados (`het-mis*`, "
                  "`half-100-156`) PERDE (Δfix>0). O ganho -23% da v1 era artefato de bloco==S.")
    linhas.append("- **Segmentação ADAPTATIVA é robusta**: coloca a fronteira ONDE o regime vira (do "
                  "run-list), então ganha em heterogêneo INDEPENDENTE de alinhamento (Δadapt<0 em todos "
                  "os het-*), e degenera pra ~1 segmento no homogêneo (Δadapt≈0, nunca-pior).")
    linhas.append("- **Custo honesto**: 'de qualquer forma' cobre SÓ o run-list (o `_rle_adjacente` já "
                  "roda no bool). O tamanho base64 e a segmentação são passo NOVO barato (O(runs), 1 "
                  "acumulador) — não reuso. E o ponto de seleção estilo `emitted_mode` é do `.8M`; o "
                  "`.8H` single-col não tem um hoje (grounding wf_876541f7).")
    linhas.append("- **Nunca-pior via FLOOR**: o +6 do seg-adapt no homogêneo é só o header `D<n>:` do "
                  "único segmento. Sob o FLOOR que o TCF já usa (emitir seg-adapt só se `< min(whole-"
                  "dense, whole-rle)`, como a nature compete), o homogêneo cai pro whole-dense e o "
                  "adaptativo vira estritamente nunca-pior — o eixo é ganhar no heterogêneo sem risco.")
    linhas.append("- **Passe único** vale pras duas composições (`reads/n==1.0`): fixo lê fatias "
                  "disjuntas; adaptativo faz 1 scan da coluna. Latência preservada.")
    linhas.append("- **Trade composição×paralelismo**: fixo = lotes independentes (paralelizável) mas "
                  "frágil; adaptativo = comprime robusto mas a fronteira depende do scan (menos "
                  "paralelizável). A telemetria informa os dois — a ESCOLHA entre eles é o vetor.")
    linhas.append(f"\n**{len(casos)} casos × {len(SIZES)} S · {falhas} falhas (RT + passe único).** "
                  "Regenera: `python run.py`.")
    (AQUI / "result.md").write_text("\n".join(linhas), encoding="utf-8", newline="\n")
    print(f"OK · {len(casos)} casos · {falhas} falhas (RT + passe unico)")
    return falhas


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)
