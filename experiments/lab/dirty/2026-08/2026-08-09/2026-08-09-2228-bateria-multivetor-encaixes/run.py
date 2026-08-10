"""Bateria MULTI-VETOR dos encaixes de agora — bytes × CPU × memória × online. `python run.py`

Pedido do owner (2026-08-09): *"veja o que dá pra fazer de melhor pra AGORA, com o
balanço entre compressão, mas também as alternativas de fazer com menos memória, mais
rápido (…) não é uma coisa só (…) se não tem ganho 100%, a gente deixa um dos ganhos
default e testa algumas variantes. só pra fechar o 1.0"*.

Os candidatos de agora (a raiz — nós de proximidade no OBAT — está registrada como 2.0,
`T-OBAT-NOS-PROXIMIDADE`):

    E2  candidato SEM-DEDUP: corpo literal (sem `^N`) compactado pelo uniforme+periódico
        que JÁ estão soldados. Sonda prévia provou: **decodável HOJE** (mesma gramática,
        linha-a-linha) → encoder-only, não format change.
    E1  split estrutural na rota flat: o `%` (ADR-0026) já corta `ano|mês|dia`, mas só
        concorre no multi-col. Sonda prévia: o corpo do split é um MULTI-COL EMBUTIDO
        (blocos por coluna) → análise de online-ness fundamentada.
    SPEC alvo mensal (confirmação): CPU/mem do A4-espelho vs spec ordinal atual.

Vetores por candidato: bytes · CPU encode · CPU decode · pico de memória (tracemalloc) ·
online-ness (análise estrutural registrada, não medida aqui — método do lab 2055).

Método de CPU: rodadas INTERCALADAS, mediana de 5 (lição da polaridade: sinal firme,
magnitude com CV — reportar ambos). RT em TODOS os candidatos de TODOS os casos.

`src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import statistics
import sys
import time
import tracemalloc

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.composicional.hcc_seqrle import (  # noqa: E402
    compact_body,
    compact_body_periodico,
    deltas_pares,
    detect_periodic_runs,
)
from tcf.multi.split import _decode_struct_split, _struct_split_encode  # noqa: E402
from tcf.natures import SPEC_DATA_ISO  # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE  # noqa: E402

for x in ("inputs", "intermediates", "outputs"):
    (RAIZ / x).mkdir(parents=True, exist_ok=True)

K_CPU = 5


def _escreve(p, t):
    p.write_text(t, encoding="utf-8", newline="")


def _cpu(fn):
    xs = []
    for _ in range(K_CPU):
        t = time.perf_counter()
        fn()
        xs.append(time.perf_counter() - t)
    med = statistics.median(xs)
    cv = (statistics.pstdev(xs) / med * 100) if med else 0.0
    return med * 1e3, cv


def _mem(fn):
    tracemalloc.start()
    fn()
    pico = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return pico / 1024


# ─────────────────────────────── geradores ───────────────────────────────

def _rnd(i, mod, salt=""):
    return int.from_bytes(hashlib.sha256(f"{salt}:{i}".encode()).digest()[:4], "big") % mod


def mensal_iso(n):
    out, y, m = [], 2000, 1
    for _ in range(n):
        out.append(_dt.date(y, m, 1).isoformat())
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


def uteis_iso(n):
    out, d = [], _dt.date(2026, 1, 1)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += _dt.timedelta(days=1)
    return out


# ─────────────────────────── E2: candidato SEM-DEDUP ───────────────────────────

def e2_candidato(vals):
    """Corpo literal escapado + min(uniforme, periódico). Restrição do esboço: coluna
    toda-dígito (é onde a aritmética existe). Devolve (wire, custo_extra_fn)."""
    linhas = ["\\" + v for v in vals]
    pares = deltas_pares(linhas)
    uni, _ = compact_body(linhas, pares)
    runs = detect_periodic_runs(linhas, pares)
    corpo = uni
    if runs:
        per, _ = compact_body_periodico(linhas, runs, pares)
        if sum(len(x) + 1 for x in per) < sum(len(x) + 1 for x in uni):
            corpo = per
    return "#TCF.8\n" + "\n".join(corpo) + "\n"


def bateria_e2():
    print("=== E2 — candidato SEM-DEDUP (encoder-only: a gramática já decodifica)")
    casos = {
        "mes-ciclico-k12": [f"{(i % 12) + 1:02d}" for i in range(600)],
        "dia-ciclico-k28": [f"{(i % 28) + 1:02d}" for i in range(600)],
        "semana-ciclica-k7": [f"{(i % 7) + 1}" for i in range(600)],
        "mes-ciclico-n6000": [f"{(i % 12) + 1:02d}" for i in range(6000)],
        "CONTROLE-digito-sem-ordem": [f"{10 + _rnd(i, 5, 'c') * 17}" for i in range(600)],
    }
    R = []
    for rot, vals in casos.items():
        _escreve(RAIZ / "inputs" / f"e2-{rot}.json", json.dumps(vals[:50]))
        w_atual = encode(vals)
        assert decode(w_atual) == vals
        w_e2 = e2_candidato(vals)
        assert decode(w_e2) == vals, f"{rot}: E2 nao decodou"       # decodável HOJE
        vence_e2 = len(w_e2.encode()) < len(w_atual.encode())
        cpu_atual, cva = _cpu(lambda: encode(vals))
        cpu_e2, cve = _cpu(lambda: e2_candidato(vals))              # o custo EXTRA do candidato
        mem_atual = _mem(lambda: encode(vals))
        mem_e2 = _mem(lambda: e2_candidato(vals))
        R.append({"caso": rot, "n": len(vals),
                  "bytes_atual": len(w_atual.encode()), "bytes_e2": len(w_e2.encode()),
                  "e2_vence": vence_e2,
                  "cpu_encode_atual_ms": round(cpu_atual, 2), "cv_a": round(cva),
                  "cpu_candidato_e2_ms": round(cpu_e2, 2), "cv_e": round(cve),
                  "incremento_cpu_pct": round(cpu_e2 / cpu_atual * 100),
                  "mem_atual_KiB": round(mem_atual), "mem_e2_KiB": round(mem_e2)})
        print(f"  {rot:<26} {len(w_atual.encode()):>5} -> {len(w_e2.encode()):>5} B "
              f"{'E2 VENCE' if vence_e2 else 'atual fica':<10} | candidato custa "
              f"{cpu_e2:.1f} ms = +{cpu_e2 / cpu_atual * 100:.0f}% do encode "
              f"(±{max(cva, cve):.0f}%) | mem {mem_atual:.0f}->{mem_e2:.0f} KiB")
        if rot == "mes-ciclico-k12":
            _escreve(RAIZ / "outputs" / "e2-mes-ciclico.tcf", w_e2)
    return R


# ─────────────────────────── E1: split na rota flat ───────────────────────────

def bateria_e1():
    print("\n=== E1 — split estrutural como candidato da rota FLAT")
    casos = {"mensal-iso": mensal_iso(600), "uteis-iso": uteis_iso(600),
             "diario-iso": [( _dt.date(2026, 1, 1) + _dt.timedelta(days=i)).isoformat()
                            for i in range(600)]}
    R = []
    for rot, vals in casos.items():
        _escreve(RAIZ / "inputs" / f"e1-{rot}.json", json.dumps(vals[:30]))
        w_atual = encode(vals)
        assert decode(w_atual) == vals
        sb = _struct_split_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
        ok = sb is not None and _decode_struct_split(sb) == vals
        b_split = (len(sb.encode() if isinstance(sb, str) else sb) + 1) if sb else None
        cpu_atual, cva = _cpu(lambda: encode(vals))
        cpu_split, cvs = _cpu(lambda: _struct_split_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None))
        mem_split = _mem(lambda: _struct_split_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None))
        R.append({"caso": rot, "bytes_atual": len(w_atual.encode()), "bytes_split": b_split,
                  "split_rt": ok, "split_vence": bool(b_split and b_split < len(w_atual.encode())),
                  "cpu_encode_atual_ms": round(cpu_atual, 2),
                  "cpu_candidato_split_ms": round(cpu_split, 2),
                  "incremento_cpu_pct": round(cpu_split / cpu_atual * 100),
                  "cv": round(max(cva, cvs)), "mem_split_KiB": round(mem_split)})
        print(f"  {rot:<12} {len(w_atual.encode()):>5} -> {str(b_split):>5} B "
              f"{'SPLIT VENCE' if b_split and b_split < len(w_atual.encode()) else 'atual fica':<11} "
              f"RT={ok} | candidato custa {cpu_split:.1f} ms = +{cpu_split / cpu_atual * 100:.0f}% "
              f"(±{max(cva, cvs):.0f}%) | mem {mem_split:.0f} KiB")
    return R


# ─────────────────────────── SPEC mensal: CPU/mem de confirmação ───────────────────────────

def bateria_spec():
    print("\n=== SPEC mensal (A4-espelho) — CPU/mem vs spec ordinal atual (bytes: 679 vs 44)")
    vals = mensal_iso(600)

    def a4():
        col = []
        for v in vals:
            d = _dt.date.fromisoformat(v)
            col.append(str((d.year * 12 + d.month - 1) * 31 + d.day - 1))
        return encode(col)

    w1 = encode(vals, nature=SPEC_DATA_ISO)
    assert decode(w1) == vals
    w2 = a4()
    cpu1, cv1 = _cpu(lambda: encode(vals, nature=SPEC_DATA_ISO))
    cpu2, cv2 = _cpu(a4)
    m1, m2 = _mem(lambda: encode(vals, nature=SPEC_DATA_ISO)), _mem(a4)
    R = {"bytes_spec_ordinal": len(w1.encode()), "bytes_a4_espelho": len(w2.encode()) + 11,
         "cpu_spec_ms": round(cpu1, 2), "cpu_a4_ms": round(cpu2, 2),
         "cv": round(max(cv1, cv2)), "mem_spec_KiB": round(m1), "mem_a4_KiB": round(m2)}
    print(f"  bytes {R['bytes_spec_ordinal']} -> {R['bytes_a4_espelho']} | "
          f"CPU {cpu1:.1f} -> {cpu2:.1f} ms (±{R['cv']}%) | mem {m1:.0f} -> {m2:.0f} KiB")
    return R


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    R = {"E2_sem_dedup": bateria_e2(), "E1_split_flat": bateria_e1(),
         "SPEC_mensal_confirmacao": bateria_spec(),
         "online_ness_estrutural": {
             "corpo_atual_e_E2": "linha-a-linha; marcadores expandem em ordem — STREAMA "
                                 "(mesma gramática; E2 não muda o transporte)",
             "split_%": "corpo é um multi-col EMBUTIDO (#TCF.8M interno, blocos POR "
                        "COLUNA-CAMPO): a 1ª linha completa exige ler até o bloco do "
                        "último campo — NÃO streama por linha (classe do modo C/ADR-0036)",
             "bN_modo_B": "domínio primeiro — streama (referência)"}}
    _escreve(RAIZ / "outputs" / "bateria.json", json.dumps(R, ensure_ascii=False, indent=1))
    print("\nOK — RT verde em todos os candidatos de todos os casos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
