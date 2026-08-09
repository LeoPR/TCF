"""Sonda de DESIGN — o periódico soldado no lugar certo. `python design_probe.py`

O `result.md` deste lab disse que o periódico precisaria de um "espelho raw" porque a
rota do candidato era `#TCF.8!!`. **Estava errado, e a correção barateia o design.**

    `!!` NÃO é rota raw — é o SUFIXO DE POLARIDADE (weld 2026-07-26), camada de BORDA
    aplicada DEPOIS de tudo. O corpo que o `compact_body` enxerga ainda tem os escapes:
        pré-polaridade   *3+1|7\\3      \\7396*\\1*\\7
        pós-polaridade   *3+1|7!3       !7396*1*7
    Logo `compare_for_seq`/`shift_escape_digits` do core servem SEM espelho novo. O lab
    anterior media do lado de fora (o wire emitido), e de fora o mundo parece raw.

Esta sonda põe o periódico ONDE ELE MORARIA — dentro do `compact_body` — via subclasse
+ monkeypatch de `tcf.encoder.HCCSeqRLE` e `tcf.decoder.HCCSeqRLE`. `src/tcf` continua
INTOCADO no disco; o que roda é o `encode`/`decode` REAIS com a camada trocada.

Serve pra responder três coisas que a medição de fora não respondia:
  1. o ganho sobrevive ao pipeline real (OBAT + HCC + polaridade + FLOOR)?
  2. o RT fecha pelo `decode()` real, sem wrapper de laboratório?
  3. o mecanismo mexe em quem NÃO é periódico (risco de GATE)?
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

import tcf.decoder as _dec  # noqa: E402
import tcf.encoder as _enc  # noqa: E402
from tcf.composicional.hcc_seqrle import (  # noqa: E402
    HCCSeqRLE,
    compact_body,
    compare_for_seq,
    expand_seq_marker,
    shift_escape_digits,
)

MAXP = 24


def _escreve(p, t):
    p.write_text(t, encoding="utf-8", newline="")


# ───────── o mecanismo, escrito como ele seria no core (escapado, sem espelho) ─────────

def detecta_periodico(body_lines):
    """Runs (start, count, padrao) onde o delta entre linhas CICLA com período p>=2.

    Restrição de escopo (deliberada): só pares de UM run de escape-digit. Multi-run
    periódico é produto cruzado com o ADR-0016 e fica de fora do 1º weld."""
    d = []
    for a, b in zip(body_lines, body_lines[1:]):
        v = compare_for_seq(a, b)
        d.append(v[0] if v is not None and len(v) == 1 else None)
    runs, i, n = [], 0, len(body_lines)
    while i < n - 1:
        if d[i] is None:
            i += 1
            continue
        j = i
        while j < n - 1 and d[j] is not None:
            j += 1
        cadeia = d[i:j]
        melhor = None
        for p in range(2, min(MAXP, len(cadeia)) + 1):
            pad = cadeia[:p]
            L = p
            while L < len(cadeia) and cadeia[L] == pad[L % p]:
                L += 1
            if L < 2 * p:            # exige 2 CICLOS completos (senão vira lista literal)
                continue
            if len(set(pad)) == 1:   # GUARDA 1: pad uniforme ([1,1]) é delta uniforme
                continue             # disfarçado — o `*N+d|` de hoje faz por menos
            cobertas = L + 1
            marcador = f"*{cobertas}~{','.join(map(str, pad))}|{body_lines[i]}"
            economia = sum(len(body_lines[i + k]) + 1 for k in range(cobertas)) - (len(marcador) + 1)
            if economia > 0 and (melhor is None or economia > melhor[0]):
                melhor = (economia, cobertas, pad)
        if melhor:
            runs.append((i, melhor[1], melhor[2]))
            i += melhor[1]
        else:
            i += 1
    return runs


def compact_body_periodico(body_lines):
    """Periódico primeiro (é o mais específico), o uniforme existente no resto."""
    runs = detecta_periodico(body_lines)
    if not runs:
        return compact_body(body_lines)
    saida, i, ri, pend = [], 0, 0, []
    def _drena():
        if pend:
            saida.extend(compact_body(pend)[0])
            pend.clear()
    while i < len(body_lines):
        if ri < len(runs) and runs[ri][0] == i:
            _drena()
            _, count, pad = runs[ri]
            saida.append(f"*{count}~{','.join(map(str, pad))}|{body_lines[i]}")
            i += count
            ri += 1
        else:
            pend.append(body_lines[i])
            i += 1
    _drena()
    return saida, []


def expande_periodico(linha):
    bar = linha.find("|")
    if not linha.startswith("*") or bar == -1:
        return None
    head = linha[1:bar]
    til = head.find("~")
    if til <= 0 or not head[:til].isdigit():
        return None
    try:
        pad = [int(x) for x in head[til + 1:].split(",")]
    except ValueError:
        return None
    count, template = int(head[:til]), linha[bar + 1:]
    out, curr = [template], template
    for k in range(1, count):
        curr = shift_escape_digits(curr, pad[(k - 1) % len(pad)])
        out.append(curr)
    return out


class SeqRLEPeriodico(HCCSeqRLE):
    """O weld hipotético: mesma classe, `compact_body` e `expand` estendidos."""

    def encode(self, linhas, unicas, tokens_por_string, header):
        body_text = super(HCCSeqRLE, self).encode(linhas, unicas, tokens_por_string, header)
        body_lines = body_text[:-1].split("\n")
        self._seq_info = []
        # GUARDA 2 — o FLOOR tem de comparar contra o CORPO JÁ COMPACTADO de hoje, não
        # contra o corpo cru. Medido nesta sonda: comparando com o cru, o periódico
        # "vencia" e piorava 4 de 8 casos (diário 32→34, ruído 203→253), porque ganhava
        # do cru e perdia do uniforme. Mesma classe do fix de baseline do FLOOR da
        # nature (2026-08-08): candidato comparado com o baseline errado.
        hoje = "\n".join(compact_body(body_lines)[0]) + "\n"
        cand = "\n".join(compact_body_periodico(body_lines)[0]) + "\n"
        return min(body_text, hoje, cand, key=lambda s: len(s.encode()))

    def decode(self, tcf_text, max_length=None):
        linhas, mexeu = [], False
        for raw in tcf_text.split("\n"):
            e = expande_periodico(raw)
            if e is not None:
                linhas.extend(e)
                mexeu = True
            else:
                linhas.append(raw)
        return super().decode("\n".join(linhas) if mexeu else tcf_text, max_length=max_length)


# ─────────────────────────────────── medição ───────────────────────────────────

def uteis(n, feriados=0):
    out, d, u = [], _dt.date(2026, 1, 1), 0
    while len(out) < n:
        if d.weekday() < 5:
            u += 1
            if not (feriados and u % 21 == 0):
                out.append(d)
        d += _dt.timedelta(days=1)
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from tcf import decode, encode
    from tcf.natures import SPEC_DATA_ISO

    B = _dt.date(2026, 1, 1)
    casos = [
        ("uteis", [d.isoformat() for d in uteis(600)]),
        ("uteis-n6000", [d.isoformat() for d in uteis(6000)]),
        ("uteis-feriado", [d.isoformat() for d in uteis(600, feriados=1)]),
        ("diario-controle", [(B + _dt.timedelta(days=i)).isoformat() for i in range(600)]),
        ("semanal-controle", [(B + _dt.timedelta(days=7 * i)).isoformat() for i in range(600)]),
        ("ids-turno", None),
        ("texto-controle", [f"cliente-{i % 37}" for i in range(600)]),
        ("ruido-alta-card", [str((i * 7919) % 999983) for i in range(600)]),
    ]
    v, ciclo = 700000, [10, 10, 10, 50]
    ids = []
    for i in range(600):
        ids.append(str(v))
        v += ciclo[i % 4]
    casos[5] = ("ids-turno", ids)

    R = []
    for rot, vals in casos:
        e_data = rot.startswith(("uteis", "diario", "semanal"))
        kw = {"nature": SPEC_DATA_ISO} if e_data else {}
        antes = encode(vals, **kw)
        assert decode(antes) == vals, f"{rot}: RT do baseline quebrou"
        _enc.HCCSeqRLE = _dec.HCCSeqRLE = SeqRLEPeriodico
        try:
            depois = encode(vals, **kw)
            rt_novo = decode(depois) == vals          # decode REAL, camada trocada
            rt_velho = decode(antes) == vals          # wire ANTIGO ainda lê (compat)
        finally:
            _enc.HCCSeqRLE = _dec.HCCSeqRLE = HCCSeqRLE
        usou = "~|" in depois or ("*" in depois and "~" in depois.split("|")[0])
        # COMPAT PRA FRENTE: o decoder de HOJE, diante do marcador novo, tem de FALHAR
        # ALTO (E3) — nunca devolver dado errado calado. Medido, não assumido.
        try:
            velho_no_novo = "aceitou-calado" if decode(depois) == vals else "DEVOLVEU-ERRADO"
        except ValueError as e:
            velho_no_novo = f"fail-loud: {str(e)[:44]}"
        R.append({"caso": rot, "n": len(vals), "antes": len(antes.encode()),
                  "depois": len(depois.encode()), "usou_periodico": usou,
                  "rt_wire_novo": rt_novo, "rt_wire_antigo": rt_velho,
                  "decoder_antigo_no_wire_novo": velho_no_novo,
                  "mudou_bytes": len(antes.encode()) != len(depois.encode())})
        if rot in ("uteis", "ids-turno"):
            _escreve(RAIZ / "outputs" / f"{rot}--periodico-no-core.tcf", depois)

    _escreve(RAIZ / "outputs" / "design-probe.json", json.dumps(R, ensure_ascii=False, indent=1))
    larg = max(len(r["caso"]) for r in R)
    print(f"{'caso'.ljust(larg)}  {'antes':>7} {'depois':>7}  {'fator':>6}  periódico  RT")
    for r in R:
        f = r["antes"] / r["depois"]
        print(f"{r['caso'].ljust(larg)}  {r['antes']:>7} {r['depois']:>7}  {f:>5.1f}x  "
              f"{'SIM' if r['usou_periodico'] else '—':^9}  "
              f"{'ok' if r['rt_wire_novo'] and r['rt_wire_antigo'] else 'FALHOU'}")
    mexeu_sem_periodo = [r["caso"] for r in R if r["mudou_bytes"] and not r["usou_periodico"]]
    print("\nMudou bytes SEM usar o periódico (risco de GATE):",
          mexeu_sem_periodo or "nenhum")
    print("Decoder de HOJE diante do wire NOVO (E3 — nunca calado):")
    for r in R:
        if r["usou_periodico"]:
            print(f"  {r['caso']}: {r['decoder_antigo_no_wire_novo']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
