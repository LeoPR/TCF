# -*- coding: utf-8 -*-
"""Onde o float ainda tem folga: mexendo na GRAFIA (lossless) ou no VALOR (loss).

    python run.py

## A pergunta

O owner (2026-08-14):

> *"tinha o caso desses floats serem colocados em loss mode, ou lossless alterando a
> distribuicao numerica... 0.2, 0.4... e aparece um 0.333333333 no meio, daria pra
> arredondar pra caber com o resto. ainda no lossless alterado... 0.333333333333 ->
> `1/3...12`... tecnicas de arredondamento financeiro que numa possivel soma ele nao muda."*

Sao DUAS ideias, e os gates sao diferentes:

- **lossless alterado** — muda so' a GRAFIA no corpo; o valor volta identico. NAO tem gate:
  e' candidato de `min()` como qualquer outro. Aqui: M1 (fracao) e M3 (escala com excecoes).
- **loss mode** — muda o VALOR. **GATEADO** (Pacote 10; formato lossless-puro por decisao do
  owner em 2026-06-15). Aqui: M4, **so' medido**, nunca proposto.

## O que este lab NAO faz

Nao propoe weld, nao toca `src/tcf/`, e nao mede ganho agregado de corpus. E' o comeco lento
que o owner pediu: casos PARTICULARES, com par de contra-prova, para ver o efeito.

## O RT que vale

Herdado do fechamento do float: `type()` E valor E **sinal do zero** (`-0.0 == 0.0` e' True;
so' `math.copysign` distingue). Para M4 o contrato e' outro — **exato-no-agregado** — e esta'
declarado como tal, nao disfarcado de RT.

## Contabilidade

Um spec sobre float emitiria `#TCF.8n :xx`; `encode([str, ...])` emite `#TCF.8`. A diferenca
e' `n :xx` = 5 B, cobrada em `CUSTO_SPEC_ID`. Para M2/M3 cobra-se tambem o expoente k.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import shutil
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from tcf import decode, encode                                    # noqa: E402
import casos as C                                                 # noqa: E402
import mecanismos as M                                            # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def _seguro(v):
    """JSON nao tem NaN/Inf; grava a grafia para o arquivo continuar diffavel."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return repr(v)
    return v


def igual_float(a, b) -> bool:
    """RT estrito: tipo E valor E sinal do zero. Do fechamento do float (1616)."""
    if a is None or len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x is None or y is None:
            if x is not y:
                return False
            continue
        if type(x) is not type(y):
            return False
        if isinstance(x, float) and math.isnan(x) and math.isnan(y):
            continue
        if isinstance(x, float) and x == 0.0 and y == 0.0:
            if math.copysign(1.0, x) != math.copysign(1.0, y):
                return False
        elif x != y:
            return False
    return True


def _hash(vals):
    return hashlib.sha256(json.dumps([_seguro(v) for v in vals]).encode()).hexdigest()[:12]


# ── a avaliacao de UM caso ───────────────────────────────────────────────────
def avalia(nome, vals, ideia, fonte, guardar_diario=True):
    falhas = []
    reg = {"caso": nome, "ideia": ideia, "n": len(vals),
           "CONSTANTE_na_comparacao": "os MESMOS valores, o MESMO encode(), o MESMO RT estrito; "
                                      "so' muda a GRAFIA que entra no corpo",
           "hash_entrada": _hash(vals)}

    # baseline — o que o nucleo faz HOJE
    try:
        w0 = encode(vals)
        rt0 = igual_float(decode(w0), vals)
        reg["baseline"] = {"bytes": B(w0), "header": w0.split("\n")[0], "rt": rt0}
        if not rt0:
            falhas.append(f"{nome}: baseline nao fez RT (o nucleo, nao o mecanismo)")
        _esc(OUT / f"{nome}.baseline.tcf", w0)
        _js(OUT / f"{nome}.roundtrip.json", [_seguro(v) for v in decode(w0)])
    except Exception as e:
        reg["baseline"] = {"recusa": f"{type(e).__name__}: {str(e)[:70]}"}
        _js(RAIZ / "_parcial.json", reg)
        return reg, falhas
    base = B(w0)

    # ── M1 — grafia fracional ────────────────────────────────────────────────
    corpo1, diarios, n1 = M.m1_coluna(vals)
    if n1:
        w1 = encode([c if c is not None else None for c in corpo1])
        b1 = B(w1) + M.CUSTO_SPEC_ID
        volta1 = M.m1_reverso(corpo1, vals)
        rt1 = igual_float(volta1, vals)
        reg["M1_fracao"] = {"convertidos": f"{n1}/{len(vals)}", "bytes": b1,
                            "delta_vs_base": b1 - base, "rt": rt1,
                            "corpo_exemplo": [c for c in corpo1 if c][:4]}
        if not rt1:
            falhas.append(f"{nome}: M1 quebrou o RT — a grafia fracional NAO e' lossless aqui")
        _esc(OUT / f"{nome}.M1-fracao.tcf", w1)
        _js(OUT / f"{nome}.M1-fracao.roundtrip.json", [_seguro(v) for v in volta1])
    else:
        reg["M1_fracao"] = {"convertidos": f"0/{len(vals)}", "recusa": "nenhum valor e' dizima"}
    if guardar_diario:
        _js(INT / f"{nome}.M1-diario.json",
            [{"valor": _seguro(v), **d} for v, d in zip(vals, diarios)])

    # ── M2 — escala pura (tudo-ou-nada) ──────────────────────────────────────
    k2, corpo2 = M.m2_escala_pura(vals)
    if k2 is not None:
        w2 = encode(corpo2)
        b2 = B(w2) + M.CUSTO_SPEC_ID + len(str(k2))
        volta2 = M.m3_reverso(corpo2, k2)
        rt2 = igual_float(volta2, vals)
        reg["M2_escala_pura"] = {"k": k2, "bytes": b2, "delta_vs_base": b2 - base, "rt": rt2}
        if not rt2:
            falhas.append(f"{nome}: M2 quebrou o RT")
        _esc(OUT / f"{nome}.M2-escala-pura.tcf", w2)
        _js(OUT / f"{nome}.M2-escala-pura.roundtrip.json", [_seguro(v) for v in volta2])
    else:
        reg["M2_escala_pura"] = {"recusa": "nenhum k <= 12 serve a TODOS os valores"}

    # ── M3 — escala com excecoes ─────────────────────────────────────────────
    cands = M.m3_escala_com_excecoes(vals)
    if cands:
        avaliados, n_encodes = [], 0
        for k, corpo, exc in cands:
            wb = encode(corpo)
            n_encodes += 1
            custo = B(wb) + M.CUSTO_SPEC_ID + len(str(k))
            avaliados.append({"k": k, "excecoes": len(exc), "bytes": custo})
            volta = M.m3_reverso(corpo, k, vals)
            if not igual_float(volta, vals):
                falhas.append(f"{nome}: M3 k={k} quebrou o RT — a excecao nao reconstroi")
        melhor = min(avaliados, key=lambda a: a["bytes"])
        k3, corpo3, exc3 = next(c for c in cands if c[0] == melhor["k"])
        w3 = encode(corpo3)
        volta3 = M.m3_reverso(corpo3, k3, vals)
        reg["M3_escala_excecoes"] = {
            "k": k3, "excecoes": f"{len(exc3)}/{len(vals)}", "bytes": melhor["bytes"],
            "delta_vs_base": melhor["bytes"] - base, "rt": igual_float(volta3, vals),
            "custo_de_busca_encodes": n_encodes,
            "corpo_exemplo": corpo3[:6]}
        _esc(OUT / f"{nome}.M3-escala-excecoes.tcf", w3)
        _js(OUT / f"{nome}.M3-escala-excecoes.roundtrip.json", [_seguro(v) for v in volta3])
        _js(INT / f"{nome}.M3-varredura-de-k.json", avaliados)
    else:
        reg["M3_escala_excecoes"] = {"recusa": "nenhum k serve nem a maioria"}

    # ── M3b — a MESMA escala, com o marcador `_` que o core ja' tem ──────────
    candsb = M.m3b_com_marcador(vals)
    if candsb:
        avaliados = []
        for k, corpo, exc in candsb:
            custo = B(encode(corpo)) + M.CUSTO_SPEC_ID + len(str(k))
            avaliados.append({"k": k, "excecoes": len(exc), "bytes": custo})
            if not igual_float(M.m3b_reverso(corpo, k), vals):
                falhas.append(f"{nome}: M3b k={k} quebrou o RT")
        melhor = min(avaliados, key=lambda a: a["bytes"])
        kb, corpob, excb = next(c for c in candsb if c[0] == melhor["k"])
        voltab = M.m3b_reverso(corpob, kb)
        reg["M3b_marcador_do_core"] = {
            "k": kb, "excecoes": f"{len(excb)}/{len(vals)}", "bytes": melhor["bytes"],
            "delta_vs_base": melhor["bytes"] - base, "rt": igual_float(voltab, vals),
            "aceita_tipo_misto": True, "corpo_exemplo": corpob[:6]}
        _esc(OUT / f"{nome}.M3b-marcador.tcf", encode(corpob))
        _js(OUT / f"{nome}.M3b-marcador.roundtrip.json", [_seguro(v) for v in voltab])
        _js(INT / f"{nome}.M3b-varredura-de-k.json", avaliados)
    else:
        reg["M3b_marcador_do_core"] = {"recusa": "nenhum k serve nem a maioria"}

    # ── o FLOOR: nunca-pior ──────────────────────────────────────────────────
    concorrentes = {"nucleo-hoje": base}
    for chave, rot in (("M1_fracao", "M1"), ("M2_escala_pura", "M2"),
                       ("M3_escala_excecoes", "M3"), ("M3b_marcador_do_core", "M3b")):
        if "bytes" in reg.get(chave, {}) and reg[chave].get("rt"):
            concorrentes[rot] = reg[chave]["bytes"]
    venc = min(concorrentes, key=concorrentes.get)
    reg["FLOOR"] = {"vencedor": venc, "bytes": concorrentes[venc],
                    "vs_hoje": concorrentes[venc] - base, "concorrentes": concorrentes}

    _js(OUT / f"{nome}.meta.json", {
        "input": f"inputs/{nome}.entrada.json", "hash_entrada": reg["hash_entrada"],
        "fonte": fonte, "n": len(vals), "baseline_bytes": base,
        "vencedor": venc, "bytes_vencedor": concorrentes[venc],
        "wires": sorted(p.name for p in OUT.glob(f"{nome}.*.tcf"))})
    return reg, falhas


# ── M4 — o loss, medido a parte (GATEADO) ───────────────────────────────────
def mede_loss(nome, vals, casas):
    ing, lr = M.m4_round_soma_preservada(vals, casas)
    if ing is None:
        return None
    soma_orig = sum(v for v in vals if v is not None)
    esc = 10 ** casas
    d_ing = round(sum(v for v in ing if v is not None) * esc) - round(soma_orig * esc)
    d_lr = round(sum(v for v in lr if v is not None) * esc) - round(soma_orig * esc)
    err = max(abs(a - b) for a, b in zip(vals, lr) if a is not None)
    err_ing = max(abs(a - b) for a, b in zip(vals, ing) if a is not None)
    b0 = B(encode(vals))
    w_lr = encode(lr)
    b_lr = B(w_lr)
    # §RT: mesmo no lossy, o FORMATO continua lossless — os valores JA' ARREDONDADOS tem
    # de atravessar o encode/decode identicos. (O PoC de junho reportou bytes sem esta
    # checagem: importou `decode` e nunca chamou.)
    rt_dos_arredondados = igual_float(decode(w_lr), lr)
    return {"casas": casas, "bytes_hoje": b0, "bytes_apos_round": b_lr,
            "reducao_pct": round(100 * (1 - b_lr / b0), 1),
            "drift_ingenuo_em_passos": d_ing, "drift_maior_resto_em_passos": d_lr,
            "soma_exata_preservada": d_lr == 0,
            "erro_max_por_linha_maior_resto": err,
            "erro_max_por_linha_ingenuo": err_ing,
            "PRECO_DA_SOMA_EXATA": "o maior-resto erra ate' 1 PASSO por linha; o ingenuo "
                                   "erra ate' 0,5. Preservar a soma custa erro por-linha.",
            "um_passo": 1 / esc,
            "rt_dos_valores_arredondados": rt_dos_arredondados,
            "CONTRATO": "exato-no-agregado — NAO e' RT contra a origem; o valor por linha MUDA"}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    registros, falhas = [], []

    def roda(nome, vals, ideia, fonte, diario=True):
        _js(INP / f"{nome}.entrada.json", [_seguro(v) for v in vals])
        _js(INP / f"{nome}.fonte.json", fonte)
        r, f = avalia(nome, vals, ideia, fonte, diario)
        registros.append(r)
        falhas.extend(f)
        fl = r.get("FLOOR", {})
        m1 = r.get("M1_fracao", {})
        m3 = r.get("M3_escala_excecoes", {})
        m3b = r.get("M3b_marcador_do_core", {})
        print(f"  {nome:26s} hoje={r['baseline']['bytes']:>6}  "
              f"M1={str(m1.get('bytes', '--')):>6} ({m1.get('convertidos', '-'):>9})  "
              f"M2={str(r.get('M2_escala_pura', {}).get('bytes', 'recusa')):>6}  "
              f"M3={str(m3.get('bytes', '--')):>6}({m3.get('excecoes', '-'):>7})  "
              f"M3b={str(m3b.get('bytes', '--')):>6}({m3b.get('excecoes', '-'):>7})  "
              f"-> {fl.get('vencedor', '?'):>11} {fl.get('vs_hoje', 0):>+6}")
        return r

    print("SINTETICOS — os casos particulares, com par de contra-prova")
    for nome, vals, ideia, par in C.SINTETICOS:
        roda(nome, vals, ideia,
             {"gerador": "casos.py::SINTETICOS", "params": {"nota": par},
              "seed": None, "ideia": ideia, "pin": "sintetico viesado por construcao"})

    print("\nBORDAS — os mecanismos recusam o que devem recusar?")
    for nome, vals, ideia in C.BORDAS:
        roda(nome, vals, ideia,
             {"gerador": "casos.py::BORDAS", "params": {}, "seed": None, "ideia": ideia,
              "pin": "herdadas do fechamento do float 2026-08-14-1616"})

    print("\nREAIS — do corpus em Z:/tcf-data (amostra espalhada, nunca LIMIT puro)")
    reais_ok = 0
    for db, tab, col, sql, ideia in C.REAIS:
        vals = C.carrega_real(db, sql)
        if not vals:
            print(f"  {db}.{col:22s} (sem Z: ou sem dado — pulado)")
            continue
        reais_ok += 1
        roda(f"real-{db}-{col}", vals, ideia,
             {"gerador": "casos.py::carrega_real", "db": db, "tabela": tab, "coluna": col,
              "sql": sql, "amostra_max": C.AMOSTRA_MAX, "ideia": ideia,
              "pin": "corpus local Z:/tcf-data/interim — nao versionado"},
             diario=False)

    # ── M4, a parte GATEADA ─────────────────────────────────────────────────
    print("\nM4 — LOSS (GATEADO: so' medicao). Contrato = exato-no-agregado, NAO RT")
    loss = {}
    alvos = [("rateio-terco", dict(C.SINTETICOS_POR_NOME).get("rateio-terco"), 2),
             ("money-2casas", dict(C.SINTETICOS_POR_NOME).get("money-2casas"), 1)]
    for nome, vals, casas in alvos:
        if vals:
            loss[nome] = mede_loss(nome, vals, casas)
    for db, tab, col, sql, _ in C.REAIS:
        if col not in ("UnitPrice", "density"):
            continue
        vals = C.carrega_real(db, sql)
        if vals:
            loss[f"real-{db}-{col}"] = mede_loss(f"real-{col}", vals,
                                                 1 if col == "UnitPrice" else 2)
    for nome, m in loss.items():
        if m:
            print(f"  {nome:26s} d={m['casas']}  bytes {m['bytes_hoje']}->{m['bytes_apos_round']}"
                  f" ({m['reducao_pct']:>5}%)  drift ingenuo={m['drift_ingenuo_em_passos']:>+4} "
                  f"passos, maior-resto={m['drift_maior_resto_em_passos']:>+2}  "
                  f"soma exata={m['soma_exata_preservada']}")
    _js(INT / "M4-loss-gateado.json", loss)

    # ── saidas ──────────────────────────────────────────────────────────────
    _js(INT / "registros.json", registros)
    _js(RAIZ / "resultado.json",
        {"registros": registros, "loss_gateado": loss, "falhas": falhas,
         "reais_carregados": reais_ok})
    linhas = ["# INDEX — grafia fracional e escala com excecoes", "",
              "Wires em `<caso>.<mecanismo>.tcf`; contra-prova em `<caso>.*.roundtrip.json`;",
              "procedencia em `<caso>.meta.json`; a decisao aberta em `../intermediates/`.", "",
              "| caso | ideia | hoje | M1 fração | M2 escala | M3 exc-grafia | "
              "M3b exc-`_` | FLOOR |",
              "|---|---|---|---|---|---|---|---|"]
    for r in registros:
        f = r.get("FLOOR", {})
        linhas.append(
            f"| [`{r['caso']}`](./{r['caso']}.baseline.tcf) | {r['ideia'][:70]} | "
            f"{r['baseline'].get('bytes', '-')} | "
            f"{r.get('M1_fracao', {}).get('bytes', '—')} | "
            f"{r.get('M2_escala_pura', {}).get('bytes', '—')} | "
            f"{r.get('M3_escala_excecoes', {}).get('bytes', '—')} | "
            f"{r.get('M3b_marcador_do_core', {}).get('bytes', '—')} | "
            f"**{f.get('vencedor', '?')}** {f.get('vs_hoje', 0):+} B |")
    _esc(OUT / "INDEX.md", "\n".join(linhas) + "\n")

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:12]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
