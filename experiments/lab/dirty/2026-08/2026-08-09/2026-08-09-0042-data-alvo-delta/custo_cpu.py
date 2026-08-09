"""Custo de CPU do detector periódico — o buraco que o ADR-0040 marcou como "a medir".

Método (lições já pagas neste projeto):
  - **rodadas INTERCALADAS**, não blocos separados. A medição da polaridade (lab
    2026-08-07-2055) deu +86/+60/+37/+11% em blocos separados e só firmou o sinal quando
    as rodadas passaram a alternar dentro de cada rodada. Magnitude de CPU aqui é frágil;
    o que se reporta é SINAL e ORDEM DE GRANDEZA, não o número na casa decimal.
  - **denominador explícito**: % do encode, não µs soltos.
  - **como a função é chamada de verdade**: `encode()` inteiro, uma coluna por chamada,
    repetido — não a função interna isolada num laço artificial.

`src/tcf` NÃO é tocado (monkeypatch, como no `design_probe`).
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import statistics
import sys
import time

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

import tcf.decoder as _d  # noqa: E402
import tcf.encoder as _e  # noqa: E402
from design_probe import SeqRLEPeriodico  # noqa: E402
from tcf.composicional.hcc_seqrle import HCCSeqRLE  # noqa: E402

REPETICOES = 7      # rodadas intercaladas
CHAMADAS = 12       # encodes por rodada (a função é chamada repetidamente na vida real)


def uteis(n, feriados=0):
    out, d, u = [], _dt.date(2026, 1, 1), 0
    while len(out) < n:
        if d.weekday() < 5:
            u += 1
            if not (feriados and u % 21 == 0):
                out.append(d)
        d += _dt.timedelta(days=1)
    return out


def _cronometra(vals, camada):
    from tcf import encode
    _e.HCCSeqRLE = _d.HCCSeqRLE = camada
    t0 = time.perf_counter()
    for _ in range(CHAMADAS):
        encode(vals)
    return (time.perf_counter() - t0) / CHAMADAS


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    B = _dt.date(2026, 1, 1)
    casos = {
        # onde o periódico GANHA (paga-se pelo que entrega)
        "uteis-600": [str(d.toordinal()) for d in uteis(600)],
        "uteis-6000": [str(d.toordinal()) for d in uteis(6000)],
        # onde ele NÃO ganha — aqui o custo é puro overhead, é o caso que importa
        "diario-600": [str((B + _dt.timedelta(days=i)).toordinal()) for i in range(600)],
        "texto-600": [f"cliente-{i % 37}@acme.com.br" for i in range(600)],
        "ruido-600": [str((i * 7919) % 999983) for i in range(600)],
    }

    R = []
    for rot, vals in casos.items():
        off, on = [], []
        for _ in range(REPETICOES):
            off.append(_cronometra(vals, HCCSeqRLE))          # intercalado:
            on.append(_cronometra(vals, SeqRLEPeriodico))     # off, on, off, on…
        _e.HCCSeqRLE = _d.HCCSeqRLE = HCCSeqRLE
        m_off, m_on = statistics.median(off), statistics.median(on)
        cv_off = statistics.pstdev(off) / m_off * 100
        cv_on = statistics.pstdev(on) / m_on * 100
        R.append({"caso": rot, "n": len(vals),
                  "off_ms": round(m_off * 1e3, 3), "on_ms": round(m_on * 1e3, 3),
                  "delta_pct": round((m_on / m_off - 1) * 100, 1),
                  "cv_off_pct": round(cv_off, 1), "cv_on_pct": round(cv_on, 1)})

    (RAIZ / "outputs" / "custo-cpu.json").write_text(
        json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8", newline="")

    print(f"{'caso':<12} {'n':>5} {'off (ms)':>9} {'on (ms)':>9} {'Δ CPU':>8}   ruído (CV)")
    for r in R:
        print(f"{r['caso']:<12} {r['n']:>5} {r['off_ms']:>9.3f} {r['on_ms']:>9.3f} "
              f"{r['delta_pct']:>+7.1f}%   ±{max(r['cv_off_pct'], r['cv_on_pct']):.0f}%")
    pior = max(R, key=lambda r: r["delta_pct"])
    print(f"\nPior overhead: {pior['caso']} {pior['delta_pct']:+.1f}% "
          f"(ruído da medição ±{max(pior['cv_off_pct'], pior['cv_on_pct']):.0f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
