"""Detector periódico v3 — custo quase zero quando ele não ganha. `python detector_v3.py`

Escada do custo (o caso que importa é o em que o periódico NÃO acha nada — o comum):

    v1  O(n²)   n=2400: 13 838 ms   (re-fatiava a cadeia a cada índice)
    v2  O(n)    n=2400:    126 ms   (fronteiras de cadeia UMA vez)
    v3  O(n)    ...e sem trabalho DUPLICADO:
          - 75% do custo do v2 era recomputar o array de deltas que o `compact_body`
            já computa. v3 computa UMA vez e usa nos dois detectores.
          - quando não há run periódico, v3 devolve o resultado de HOJE sem recompactar.

`src/tcf` NÃO é tocado. O que o weld leva é o algoritmo, não este arquivo.
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
import tcf.composicional.hcc_seqrle as H  # noqa: E402
import tcf.decoder as _d  # noqa: E402
import tcf.encoder as _e  # noqa: E402
from tcf.composicional.hcc_seqrle import HCCSeqRLE, compact_body, compare_for_seq  # noqa: E402

MAX_PERIODO = 24


def _marcador(count, padrao, template):
    return f"*{count}~{','.join(str(d) for d in padrao)}|{template}"


def deltas_da_coluna(lines):
    """O array que os DOIS detectores consomem. No weld ele é computado uma vez e passa
    para o uniforme e para o periódico — hoje cada um chama `compare_for_seq` por conta."""
    out = []
    for a, b in zip(lines, lines[1:]):
        v = compare_for_seq(a, b)
        out.append(v[0] if v is not None and len(v) == 1 else None)
    return out


def detecta_periodico_v3(lines, d):
    """Recebe o array de deltas pronto. O(n · MAX_PERIODO)."""
    n, runs, i = len(lines), [], 0
    while i < n - 1:
        if d[i] is None:
            i += 1
            continue
        fim = i
        while fim < n - 1 and d[fim] is not None:
            fim += 1
        pos = i
        while pos < fim:
            melhor = None
            for p in range(2, min(MAX_PERIODO, fim - pos) + 1):
                pad = d[pos:pos + p]
                if len(set(pad)) == 1:
                    continue
                L = p
                while pos + L < fim and d[pos + L] == pad[L % p]:
                    L += 1
                if L < 2 * p:
                    continue
                count = L + 1
                custo = len(_marcador(count, pad, lines[pos])) + 1
                economia = sum(len(lines[pos + k]) + 1 for k in range(count)) - custo
                if economia > 0 and (melhor is None or economia > melhor[0]):
                    melhor = (economia, count, pad)
            if melhor is None:
                pos += 1
            else:
                runs.append((pos, melhor[1], melhor[2]))
                pos += melhor[1]
        i = max(fim, i + 1)
    return runs


class SeqRLEPeriodicoV3(HCCSeqRLE):
    def encode(self, linhas, unicas, tokens_por_string, header):
        body_text = super(HCCSeqRLE, self).encode(linhas, unicas, tokens_por_string, header)
        body_lines = body_text[:-1].split("\n")
        compactado, info = compact_body(body_lines)
        self._seq_info = info
        hoje = "\n".join(compactado) + "\n"

        runs = detecta_periodico_v3(body_lines, deltas_da_coluna(body_lines))
        if not runs:
            # SAÍDA CURTA: sem run periódico, a decisão é EXATAMENTE a de hoje —
            # zero recompactação, zero candidato a mais no min().
            return hoje if len(hoje.encode()) <= len(body_text.encode()) else body_text

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
        cand = "\n".join(saida) + "\n"
        # ORDEM load-bearing: `hoje` primeiro preserva a preferência atual em empates
        return min(hoje, body_text, cand, key=lambda s: len(s.encode("utf-8")))


def _liga(c):
    _e.HCCSeqRLE = _d.HCCSeqRLE = c


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _orig = H.expand_seq_marker

    def _expand(linha):
        p = dp.expande_periodico(linha)
        return p if p is not None else _orig(linha)
    H.expand_seq_marker = _expand

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

    import detector_v2 as D2
    print("=== CUSTO no caso em que o periódico NÃO ganha (diário uniforme) ===")
    print(f"{'n':>5} {'off':>8} {'v1':>10} {'v2':>8} {'v3':>8}   v3/off")
    for n in (600, 1200, 2400):
        vals = [str((B + _dt.timedelta(days=i)).toordinal()) for i in range(n)]
        t = {}
        for rot, cam in (("off", HCCSeqRLE), ("v1", dp.SeqRLEPeriodico),
                         ("v2", D2.SeqRLEPeriodicoV2), ("v3", SeqRLEPeriodicoV3)):
            _liga(cam)
            t0 = time.perf_counter()
            encode(vals)
            t[rot] = (time.perf_counter() - t0) * 1e3
        _liga(HCCSeqRLE)
        print(f"{n:>5} {t['off']:>8.1f} {t['v1']:>10.1f} {t['v2']:>8.1f} {t['v3']:>8.1f}   "
              f"{t['v3'] / t['off']:.2f}x")

    print("\n=== BYTES e RT: v3 tem de dar o mesmo que v1/v2 ===")
    casos = {
        "uteis-600": [d.isoformat() for d in uteis(600)],
        "uteis-feriado": [d.isoformat() for d in uteis(600, feriados=1)],
        "ids-turno": None,
        "diario-600": [(B + _dt.timedelta(days=i)).isoformat() for i in range(600)],
        "texto-600": [f"cliente-{i % 37}@acme.com.br" for i in range(600)],
        "ruido-600": [str((i * 7919) % 999983) for i in range(600)],
    }
    v, ciclo, ids = 700000, [10, 10, 10, 50], []
    for i in range(600):
        ids.append(str(v))
        v += ciclo[i % 4]
    casos["ids-turno"] = ids

    print(f"{'caso':<15} {'off':>7} {'v1':>7} {'v3':>7}   RT")
    todos_ok = True
    for rot, vals in casos.items():
        b = {}
        for k, cam in (("off", HCCSeqRLE), ("v1", dp.SeqRLEPeriodico), ("v3", SeqRLEPeriodicoV3)):
            _liga(cam)
            w = encode(vals)
            b[k] = len(w.encode())
            if k == "v3":
                rt = decode(w) == vals
        _liga(HCCSeqRLE)
        ok = b["v1"] == b["v3"] and rt
        todos_ok &= ok
        print(f"{rot:<15} {b['off']:>7} {b['v1']:>7} {b['v3']:>7}   {rt}"
              f"{'' if b['v1'] == b['v3'] else '   <-- DIVERGE de v1'}")

    print("\n=== GATES com v3 ===")
    import csv
    FROZEN = {"D1-emails-simples": 125, "D2-emails-quote-id": 173, "D3-stress-substring": 184,
              "D4-caos-mix": 120, "D5-padroes-multiplos": 267, "D6-poucos-em-ruido": 274,
              "D7-aninhamento": 222, "D8-cabeca-cauda": 107, "D9-frequencia-alta": 73}
    tot = 0
    for nome in FROZEN:
        with (REPO / "datasets" / "synthetic" / f"{nome}.csv").open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            vals = [row[0] for row in r if row]
        _liga(SeqRLEPeriodicoV3)
        tot += len(encode(vals).encode())
        _liga(HCCSeqRLE)
    print(f"D1-D9 = {tot} (congelado 1545) -> {'IGUAL' if tot == 1545 else 'MUDOU'}")

    rw = {"online-retail/description-2k.csv": 27588, "online-retail/stockcode-2k.csv": 11237,
          "tpch-sf001/lcomment-2k.csv": 50605}
    trw = 0
    for rel in rw:
        with (REPO / "datasets" / "samples" / rel).open(encoding="utf-8", newline="") as f:
            r = csv.reader(f)
            next(r)
            vals = [row[0] for row in r]
        _liga(SeqRLEPeriodicoV3)
        trw += len(encode(vals).encode())
        _liga(HCCSeqRLE)
    print(f"real-world = {trw} (congelado 89430) -> {'IGUAL' if trw == 89430 else 'MUDOU'}")
    print(f"\n{'TUDO OK' if todos_ok and tot == 1545 and trw == 89430 else 'REVISAR'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
