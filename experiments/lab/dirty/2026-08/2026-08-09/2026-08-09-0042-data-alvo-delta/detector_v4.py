"""Detector periódico v4 — o custo finalmente cai a quase zero. `python detector_v4.py`

Escada completa do custo, no caso que importa (diário uniforme: o periódico NUNCA ganha,
então tudo que ele gasta é puro overhead):

    v1   O(n²)                 n=2400: 13 838 ms   re-fatiava a cadeia a cada índice
    v2   O(n·P)                n=2400:    126 ms   fronteiras de cadeia UMA vez
    v3   idem + saída curta    n=2400:    101 ms   sem recompactar quando não há run
    v4   idem + salto uniforme n=2400:      ? ms   ver medição abaixo

O que a v4 conserta (achado da instrumentação POR DENTRO da camada — a medição isolada
mentia porque reconstruía o corpo sem o hint de cadência, e o corpo real tem UMA cadeia
de 1199 deltas):

    a lógica de período custava 19,5 ms num corpo de 1200 linhas, e QUASE TUDO era o
    guard de padrão uniforme rodando por (posição × período): 1199 posições × 23
    períodos = ~27 600 fatias e `set()` só para concluir "é uniforme, pule".

v4: pré-calcula, em O(n), a distância até a PRÓXIMA MUDANÇA de delta. Qualquer período
menor ou igual a essa distância tem padrão uniforme por construção — então o laço de `p`
começa depois dela, e numa cadeia uniforme ele nem roda.

Resultado idêntico em bytes (é a MESMA decisão, só sem trabalho jogado fora).
"""
from __future__ import annotations

import datetime as _dt
import pathlib
import statistics
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
from tcf.composicional.hcc_seqrle import HCCSeqRLE, compact_body  # noqa: E402

MAX_PERIODO = 24


def _marcador(count, padrao, template):
    return f"*{count}~{','.join(str(d) for d in padrao)}|{template}"


def detecta_periodico_v4(lines, d):
    """`d` = array de deltas (compartilhado com o detector uniforme no weld)."""
    n = len(lines)
    m = len(d)

    # PRE-CALCULO O(n): mudanca[k] = distancia de k ate' o proximo indice com delta
    # DIFERENTE de d[k]. Um periodo p <= mudanca[k] tem padrao uniforme por construcao.
    mudanca = [0] * m
    k = m - 1
    while k >= 0:
        if k == m - 1 or d[k] != d[k + 1]:
            mudanca[k] = 1
        else:
            mudanca[k] = mudanca[k + 1] + 1
        k -= 1

    runs, i = [], 0
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
            # SALTO: p menor/igual a' distancia da proxima mudanca => padrao uniforme.
            p_min = mudanca[pos] + 1
            for p in range(max(2, p_min), min(MAX_PERIODO, fim - pos) + 1):
                pad = d[pos:pos + p]
                if len(set(pad)) == 1:      # guarda 1 (agora quase nunca dispara)
                    continue
                L = p
                while pos + L < fim and d[pos + L] == pad[L % p]:
                    L += 1
                if L < 2 * p:               # dois ciclos completos
                    continue
                count = L + 1
                custo = len(_marcador(count, pad, lines[pos])) + 1
                economia = sum(len(lines[pos + k2]) + 1 for k2 in range(count)) - custo
                if economia > 0 and (melhor is None or economia > melhor[0]):
                    melhor = (economia, count, pad)
            if melhor is None:
                pos += 1
            else:
                runs.append((pos, melhor[1], melhor[2]))
                pos += melhor[1]
        i = max(fim, i + 1)
    return runs


class SeqRLEPeriodicoV4(HCCSeqRLE):
    def encode(self, linhas, unicas, tokens_por_string, header):
        from design_probe import compact_body_periodico  # noqa: F401  (só p/ paridade)
        body_text = super(HCCSeqRLE, self).encode(linhas, unicas, tokens_por_string, header)
        body_lines = body_text[:-1].split("\n")
        compactado, info = compact_body(body_lines)
        self._seq_info = info
        hoje = "\n".join(compactado) + "\n"

        import detector_v3 as D3
        runs = detecta_periodico_v4(body_lines, D3.deltas_da_coluna(body_lines))
        if not runs:
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

    import detector_v3 as D3
    from tcf import decode, encode
    B = _dt.date(2026, 1, 1)

    def uteis(n, feriados=0):
        out, dd, u = [], B, 0
        while len(out) < n:
            if dd.weekday() < 5:
                u += 1
                if not (feriados and u % 21 == 0):
                    out.append(dd)
            dd += _dt.timedelta(days=1)
        return out

    def med(camada, vals, k=7):
        xs = []
        for _ in range(k):
            _liga(camada)
            t = time.perf_counter()
            encode(vals)
            xs.append(time.perf_counter() - t)
        _liga(HCCSeqRLE)
        return statistics.median(xs) * 1e3

    print("=== CUSTO no caso em que o periódico NÃO ganha (diário uniforme) ===")
    print("    rodadas intercaladas, mediana de 7")
    print(f"{'n':>5} {'off':>8} {'v3':>8} {'v4':>8}   v4 vs off")
    for n in (600, 1200, 2400):
        vals = [str((B + _dt.timedelta(days=i)).toordinal()) for i in range(n)]
        o = med(HCCSeqRLE, vals)
        t3 = med(D3.SeqRLEPeriodicoV3, vals)
        t4 = med(SeqRLEPeriodicoV4, vals)
        print(f"{n:>5} {o:>8.1f} {t3:>8.1f} {t4:>8.1f}   {(t4 / o - 1) * 100:+.1f}%")

    print("\n=== e no caso em que ele GANHA (dias úteis) ===")
    for n in (600, 2400):
        vals = [str(dd.toordinal()) for dd in uteis(n)]
        o = med(HCCSeqRLE, vals)
        t4 = med(SeqRLEPeriodicoV4, vals)
        _liga(SeqRLEPeriodicoV4)
        w = encode(vals)
        _liga(HCCSeqRLE)
        print(f"  n={n:>5}: off {o:>7.1f} ms -> v4 {t4:>7.1f} ms ({(t4 / o - 1) * 100:+.0f}% CPU) "
              f"| bytes {len(encode(vals).encode()):>6} -> {len(w.encode()):>4}")

    print("\n=== BYTES/RT: v4 == v1 (mesma decisão, só sem desperdício) ===")
    v, ciclo, ids = 700000, [10, 10, 10, 50], []
    for i in range(600):
        ids.append(str(v))
        v += ciclo[i % 4]
    casos = {
        "uteis-600": [dd.isoformat() for dd in uteis(600)],
        "uteis-feriado": [dd.isoformat() for dd in uteis(600, feriados=1)],
        "ids-turno": ids,
        "diario-600": [(B + _dt.timedelta(days=i)).isoformat() for i in range(600)],
        "texto-600": [f"cliente-{i % 37}@acme.com.br" for i in range(600)],
        "ruido-600": [str((i * 7919) % 999983) for i in range(600)],
    }
    ok_geral = True
    print(f"{'caso':<15} {'off':>7} {'v1':>7} {'v4':>7}   RT")
    for rot, vals in casos.items():
        b = {}
        for k, cam in (("off", HCCSeqRLE), ("v1", dp.SeqRLEPeriodico), ("v4", SeqRLEPeriodicoV4)):
            _liga(cam)
            w = encode(vals)
            b[k] = len(w.encode())
            if k == "v4":
                rt = decode(w) == vals
        _liga(HCCSeqRLE)
        ok_geral &= (b["v1"] == b["v4"] and rt)
        print(f"{rot:<15} {b['off']:>7} {b['v1']:>7} {b['v4']:>7}   {rt}"
              f"{'' if b['v1'] == b['v4'] else '  <-- DIVERGE'}")

    print("\n=== GATES com v4 ===")
    import csv
    FROZEN = ["D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring", "D4-caos-mix",
              "D5-padroes-multiplos", "D6-poucos-em-ruido", "D7-aninhamento",
              "D8-cabeca-cauda", "D9-frequencia-alta"]
    tot = 0
    for nome in FROZEN:
        with (REPO / "datasets" / "synthetic" / f"{nome}.csv").open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            vals = [row[0] for row in r if row]
        _liga(SeqRLEPeriodicoV4)
        tot += len(encode(vals).encode())
        _liga(HCCSeqRLE)
    trw = 0
    for rel in ("online-retail/description-2k.csv", "online-retail/stockcode-2k.csv",
                "tpch-sf001/lcomment-2k.csv"):
        with (REPO / "datasets" / "samples" / rel).open(encoding="utf-8", newline="") as f:
            r = csv.reader(f)
            next(r)
            vals = [row[0] for row in r]
        _liga(SeqRLEPeriodicoV4)
        trw += len(encode(vals).encode())
        _liga(HCCSeqRLE)
    print(f"D1-D9 = {tot} (1545) -> {'IGUAL' if tot == 1545 else 'MUDOU'}")
    print(f"real-world = {trw} (89430) -> {'IGUAL' if trw == 89430 else 'MUDOU'}")
    print(f"\n{'TUDO OK' if ok_geral and tot == 1545 and trw == 89430 else 'REVISAR'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
