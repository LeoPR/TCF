"""Detector periódico v2 — o conserto do quadrático. `python detector_v2.py`

O `design_probe.py` (v1) mediu o GANHO certo, mas o detector dele é **O(n²)** no caso em
que ele NÃO acha nada — que é o caso comum. Medido: coluna diária (delta uniforme, o
periódico nunca vence) com a camada ligada:

    n= 300   164 ms      n=1200   3 216 ms
    n= 600   753 ms      n=2400  13 518 ms      (dobrar n -> 4,2x = quadrático)

contra 5,7 / 15 / 27 / 47 ms do encode normal. **63x no n=600, 285x no n=2400.**

Duas causas, ambas por índice em vez de por cadeia:
  1. `while j < n-1 and d[j] is not None` — reachava o fim da cadeia a CADA i;
  2. `cadeia = d[i:j]` — copiava a cadeia inteira a CADA i.

v2: fronteiras de cadeia calculadas UMA vez; dentro da cadeia, índices absolutos e
fatia só do padrão (limitada por MAX_PERIODO=24). Resultado idêntico em bytes — o que
muda é só o custo.
"""
from __future__ import annotations

import datetime as _dt
import pathlib
import sys
import time

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

import design_probe as dp  # noqa: E402
import tcf.decoder as _d  # noqa: E402
import tcf.encoder as _e  # noqa: E402
from tcf.composicional.hcc_seqrle import HCCSeqRLE, compact_body, compare_for_seq  # noqa: E402

MAX_PERIODO = 24


def _marcador(count, padrao, template):
    return f"*{count}~{','.join(str(d) for d in padrao)}|{template}"


def detecta_periodico_v2(lines):
    """Mesma saída do v1, custo O(n · MAX_PERIODO) em vez de O(n²)."""
    n = len(lines)
    d = []
    for a, b in zip(lines, lines[1:]):
        v = compare_for_seq(a, b)
        d.append(v[0] if v is not None and len(v) == 1 else None)

    runs, i = [], 0
    while i < n - 1:
        if d[i] is None:
            i += 1
            continue
        fim = i                       # fronteira da cadeia: UMA vez por cadeia
        while fim < n - 1 and d[fim] is not None:
            fim += 1
        pos = fim_anterior = i
        while pos < fim:
            melhor = None             # (economia, count, padrao)
            for p in range(2, min(MAX_PERIODO, fim - pos) + 1):
                pad = d[pos:pos + p]              # fatia LIMITADA por MAX_PERIODO
                if len(set(pad)) == 1:            # guarda 1: uniforme é do `*N+d|`
                    continue
                L = p
                while pos + L < fim and d[pos + L] == pad[L % p]:
                    L += 1
                if L < 2 * p:                     # exige 2 ciclos completos
                    continue
                count = L + 1
                marcador = _marcador(count, pad, lines[pos])
                economia = sum(len(lines[pos + k]) + 1 for k in range(count)) - (len(marcador) + 1)
                if economia > 0 and (melhor is None or economia > melhor[0]):
                    melhor = (economia, count, pad)
            if melhor is None:
                pos += 1
            else:
                runs.append((pos, melhor[1], melhor[2]))
                pos += melhor[1]
        i = fim if fim > fim_anterior else i + 1
    return runs


def compact_v2(body_lines):
    runs = detecta_periodico_v2(body_lines)
    if not runs:
        return compact_body(body_lines)
    saida, pend, i, ri = [], [], 0, 0

    def _drena():
        if pend:
            saida.extend(compact_body(pend)[0])
            pend.clear()

    while i < len(body_lines):
        if ri < len(runs) and runs[ri][0] == i:
            _drena()
            _, count, pad = runs[ri]
            saida.append(_marcador(count, pad, body_lines[i]))
            i += count
            ri += 1
        else:
            pend.append(body_lines[i])
            i += 1
    _drena()
    return saida, []


class SeqRLEPeriodicoV2(HCCSeqRLE):
    """v2: detector linear + colocação certa do expand (teto de memória preservado)."""

    def encode(self, linhas, unicas, tokens_por_string, header):
        body_text = super(HCCSeqRLE, self).encode(linhas, unicas, tokens_por_string, header)
        body_lines = body_text[:-1].split("\n")
        self._seq_info = []
        hoje = "\n".join(compact_body(body_lines)[0]) + "\n"
        cand = "\n".join(compact_v2(body_lines)[0]) + "\n"
        # ORDEM load-bearing: `hoje` primeiro preserva a preferência atual em empates
        return min(hoje, body_text, cand, key=lambda s: len(s.encode("utf-8")))


def _liga(camada):
    _e.HCCSeqRLE = _d.HCCSeqRLE = camada


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # o expand periódico vive DENTRO do expand do core (ADR-0040): preserva o teto
    _orig = sys.modules["tcf.composicional.hcc_seqrle"].expand_seq_marker

    def _expand(linha):
        p = dp.expande_periodico(linha)
        return p if p is not None else _orig(linha)
    sys.modules["tcf.composicional.hcc_seqrle"].expand_seq_marker = _expand

    from tcf import decode, encode
    B = _dt.date(2026, 1, 1)

    def uteis(n, feriados=0):
        out, d, u = [], B, 0
        while len(out) < n:
            if d.weekday() < 5:
                u += 1
                if not (feriados and u % 21 == 0):
                    out.append(d)
            d += _dt.timedelta(days=1)
        return out

    print("=== CUSTO: o caso onde o periódico NÃO ganha (diário, delta uniforme) ===")
    print(f"{'n':>5} {'off (ms)':>9} {'v1 (ms)':>10} {'v2 (ms)':>9} {'v2 vs off':>10}")
    for n in (300, 600, 1200, 2400):
        vals = [str((B + _dt.timedelta(days=i)).toordinal()) for i in range(n)]
        tempos = {}
        for rot, cam in (("off", HCCSeqRLE), ("v1", dp.SeqRLEPeriodico), ("v2", SeqRLEPeriodicoV2)):
            _liga(cam)
            t = time.perf_counter()
            encode(vals)
            tempos[rot] = (time.perf_counter() - t) * 1e3
        _liga(HCCSeqRLE)
        print(f"{n:>5} {tempos['off']:>9.1f} {tempos['v1']:>10.1f} {tempos['v2']:>9.1f} "
              f"{tempos['v2'] / tempos['off']:>9.2f}x")

    print("\n=== BYTES: v2 tem de dar o MESMO que v1 (o conserto é só de custo) ===")
    casos = {
        "uteis-600": [d.isoformat() for d in uteis(600)],
        "uteis-feriado": [d.isoformat() for d in uteis(600, feriados=1)],
        "diario-600": [(B + _dt.timedelta(days=i)).isoformat() for i in range(600)],
        "texto-600": [f"cliente-{i % 37}@acme.com.br" for i in range(600)],
        "ruido-600": [str((i * 7919) % 999983) for i in range(600)],
    }
    print(f"{'caso':<15} {'off':>7} {'v1':>7} {'v2':>7}   RT v2")
    for rot, vals in casos.items():
        b = {}
        for k, cam in (("off", HCCSeqRLE), ("v1", dp.SeqRLEPeriodico), ("v2", SeqRLEPeriodicoV2)):
            _liga(cam)
            w = encode(vals)
            b[k] = len(w.encode())
            if k == "v2":
                rt = decode(w) == vals
        _liga(HCCSeqRLE)
        flag = "" if b["v1"] == b["v2"] else "   <-- DIVERGE"
        print(f"{rot:<15} {b['off']:>7} {b['v1']:>7} {b['v2']:>7}   {rt}{flag}")

    print("\n=== GATES com v2 ===")
    import csv
    tot = 0
    FROZEN = {"D1-emails-simples": 125, "D2-emails-quote-id": 173, "D3-stress-substring": 184,
              "D4-caos-mix": 120, "D5-padroes-multiplos": 267, "D6-poucos-em-ruido": 274,
              "D7-aninhamento": 222, "D8-cabeca-cauda": 107, "D9-frequencia-alta": 73}
    for nome in FROZEN:
        with (REPO / "datasets" / "synthetic" / f"{nome}.csv").open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            vals = [row[0] for row in r if row]
        _liga(SeqRLEPeriodicoV2)
        w = encode(vals)
        _liga(HCCSeqRLE)
        tot += len(w.encode())
    print(f"D1-D9 total = {tot} (congelado 1545) -> {'IGUAL' if tot == 1545 else 'MUDOU'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
