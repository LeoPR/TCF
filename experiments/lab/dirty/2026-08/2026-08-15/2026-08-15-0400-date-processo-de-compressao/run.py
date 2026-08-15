# -*- coding: utf-8 -*-
"""DATE — o processo de compressão, com o formato FIXO e todos os candidatos no mesmo `min()`.

    python run.py

## O pedido (owner, 2026-08-15)

> *"a gente pode fazer o **mínimo** pra sustentar o ponto de vista de **compressão**: a gente vê
> o formato mais comum e se sustenta nele pra ver o processo de compressão primeiro. Se tudo
> isso funcionar, aí depois a gente ajusta entradas e saídas."*
>
> *"o core do tcf vai tratar a data de outra forma, **com permissão de transformação** se isso
> significa obter compressões melhores, e isso **não se mistura com a entrada e saída**."*

**Formato fixo**: `YYYY-MM-DD` (já decidido e welded). **Nada de entrada/saída aqui.**

## O gap que este lab fecha

O date é o tipo mais medido do projeto — ordinal, delta de coluna, periódico, alvos mensais,
split, bN, epoch, base-80. Mas o levantamento mostrou que **cada um foi medido contra o
ordinal, nunca todos no mesmo `min()`** (item 7 do gap). E **delta-of-delta nunca foi medido**
(item 1).

Este lab põe os 6 candidatos para competirem no mesmo FLOOR, sobre 14 regimes, e mede:

- **por candidato**: quanto cada leitura da coluna custa;
- **o `min()` de todos**: o que um FLOOR completo escolheria;
- **quanto se perde hoje**: `min(todos)` contra `min(o que a rota single-col tem hoje)`.

## O que NÃO está aqui

Entrada/saída, grafia, decode tipado, spec novo. Por decisão do owner: primeiro a compressão.
E `src/tcf` continua intocado — as transformações são funções de coluna do lab.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import shutil
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from tcf import decode, encode                                     # noqa: E402
from tcf.composicional.dominio_bn import candidatos as _bn_cands   # noqa: E402
from tcf.multi.core import DEFAULT_PIPELINE                        # noqa: E402
from tcf.natures import SPEC_DATA_ISO                              # noqa: E402
import transformacoes as T                                         # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
N = 600


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


# ── os 14 regimes (os que o projeto já catalogou) ───────────────────────────
BASE = _dt.date(2024, 1, 1)


def _iso(ds):
    return [d.isoformat() for d in ds]


def _lcg(sem=7):
    x = sem
    while True:
        x = (x * 1103515245 + 12345) % 2147483648
        yield x


def r_diaria(n=N):
    return _iso([BASE + _dt.timedelta(days=i) for i in range(n)])


def r_semanal(n=N):
    return _iso([BASE + _dt.timedelta(weeks=i) for i in range(n)])


def r_quinzenal(n=N):
    return _iso([BASE + _dt.timedelta(days=15 * i) for i in range(n)])


def r_mensal_dia1(n=N):
    fora, a, m = [], 2000, 1
    for _ in range(n):
        fora.append(_dt.date(a, m, 1))
        m += 1
        if m > 12:
            m, a = 1, a + 1
    return _iso(fora)


def r_mensal_faltas(n=N):
    g, fora, a, m = _lcg(11), [], 2000, 1
    while len(fora) < n:
        if next(g) % 10:                       # 10% de faltas
            fora.append(_dt.date(a, m, 1))
        m += 1
        if m > 12:
            m, a = 1, a + 1
    return _iso(fora)


def r_uteis(n=N):
    fora, d = [], BASE
    while len(fora) < n:
        if d.weekday() < 5:
            fora.append(d)
        d += _dt.timedelta(days=1)
    return _iso(fora)


def r_uteis_feriado(n=N):
    g, fora, d = _lcg(13), [], BASE
    while len(fora) < n:
        if d.weekday() < 5 and next(g) % 50:   # ~2% de feriado
            fora.append(d)
        d += _dt.timedelta(days=1)
    return _iso(fora)


def r_trimestral(n=N):
    fora, a, m = [], 2000, 1
    for _ in range(n):
        fora.append(_dt.date(a, m, 1))
        m += 3
        while m > 12:
            m, a = m - 12, a + 1
    return _iso(fora)


def r_descendente(n=N):
    return _iso([BASE - _dt.timedelta(days=i) for i in range(n)])


def r_agrupada(n=N):
    return _iso([BASE + _dt.timedelta(days=i // 20) for i in range(n)])


def r_ciclica(n=N):
    return _iso([_dt.date(2024, 1 + (i % 12), 1 + (i % 28)) for i in range(n)])


def r_esparsa_ord(n=N):
    g, fora, d = _lcg(17), [], BASE
    for _ in range(n):
        d += _dt.timedelta(days=1 + next(g) % 40)
        fora.append(d)
    return _iso(fora)


def r_esparsa_desord(n=N):
    v = r_esparsa_ord(n)
    g = _lcg(23)
    v = list(v)
    for i in range(len(v) - 1, 0, -1):
        j = next(g) % (i + 1)
        v[i], v[j] = v[j], v[i]
    return v


def r_suja(n=N):
    g, base = _lcg(29), r_diaria(n)
    return [b if next(g) % 10 else f"{b[:4]}-{b[5:7]}-{b[8:]}x"[:10] for b in base]


REGIMES = [
    ("diaria", r_diaria, "passo +1 — o caso canônico"),
    ("semanal", r_semanal, "passo +7"),
    ("quinzenal", r_quinzenal, "passo +15"),
    ("mensal-dia1", r_mensal_dia1, "dia 1 de cada mês — deltas 28..31, o ciclo REAL"),
    ("mensal-faltas", r_mensal_faltas, "mensal com 10% de meses ausentes"),
    ("uteis", r_uteis, "dias úteis — ciclo 1,3,1,1,1"),
    ("uteis-feriado", r_uteis_feriado, "úteis + ~2% de feriado (quebra o ciclo)"),
    ("trimestral", r_trimestral, "de 3 em 3 meses"),
    ("descendente", r_descendente, "passo −1"),
    ("agrupada", r_agrupada, "cada data repetida 20× — o dedup resolve"),
    ("ciclica", r_ciclica, "mês e dia CICLAM — o `T-CANDIDATO-SEM-DEDUP`"),
    ("esparsa-ordenada", r_esparsa_ord, "saltos de 1..40 dias, crescente"),
    ("esparsa-desordenada", r_esparsa_desord, "os mesmos, embaralhados"),
    ("suja", r_suja, "10% não-canônicas — o spec recusa esses valores"),
]


def mede_candidato(datas, rot, tfn, ifn):
    """Aplica a transformação, encoda, e valida o RT pela inversa."""
    vals = tfn(datas)
    if vals is None:
        return None, None, "(não se aplica)"
    w = encode(vals)
    try:
        volta = ifn(decode(w))
    except Exception as e:
        return B(w), False, f"inversa falhou: {type(e).__name__}"
    return B(w), volta == list(datas), w.split("\n")[0]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    falhas, reg = [], []
    ROTS = [r for r, _, _, _ in T.TRANSFORMACOES]

    cab = (f"  {'regime':>21} " + " ".join(f"{r:>11}" for r in ROTS)
           + f" | {'spec(hoje)':>10} {'bN':>7} | {'min(todos)':>10} {'perda-hoje':>10}")
    print("O PROCESSO DE COMPRESSÃO — cada candidato isolado, e o `min()` de todos\n")
    print(cab)
    for nome, gen, ideia in REGIMES:
        datas = gen()
        _js(INP / f"{nome}.entrada.json", datas)
        _js(INP / f"{nome}.fonte.json",
            {"gerador": "run.py::REGIMES", "regime": nome, "ideia": ideia, "n": len(datas),
             "distintos": len(set(datas)), "grafia": "YYYY-MM-DD (FIXA)",
             "seed": "LCG determinístico, sem random",
             "pin": "sintético viesado por construção"})
        linha = {"regime": nome, "ideia": ideia, "n": len(datas),
                 "distintos": len(set(datas)),
                 "CONSTANTE_na_comparacao": "a MESMA coluna e o MESMO encode; "
                                            "só muda a TRANSFORMAÇÃO aplicada antes"}
        # os 6 candidatos de transformação
        for rot, tfn, ifn, _id in T.TRANSFORMACOES:
            b, rt, hdr = mede_candidato(datas, rot, tfn, ifn)
            linha[rot] = b
            linha[f"{rot}_rt"] = rt
            linha[f"{rot}_hdr"] = hdr
            if rt is False:
                falhas.append(f"{nome}/{rot}: RT não fechou")
            if b is not None:
                vals = tfn(datas)
                _esc(OUT / f"{nome}.{rot}.tcf", encode(vals))
        # o que a rota de HOJE tem: núcleo e o spec welded
        w_spec = encode(datas, nature=SPEC_DATA_ISO)
        if decode(w_spec, nature=SPEC_DATA_ISO) != datas:
            falhas.append(f"{nome}/spec: RT do spec welded não fechou")
        linha["spec_hoje"] = B(w_spec)
        linha["spec_hdr"] = w_spec.split("\n")[0]
        _esc(OUT / f"{nome}.spec-welded.tcf", w_spec)
        _js(OUT / f"{nome}.roundtrip.json", decode(w_spec, nature=SPEC_DATA_ISO))
        # bN sobre a grafia crua (o candidato de igualdade)
        c = _bn_cands(datas, lambda vs: __import__("tcf.encoder", fromlist=["_encode_column"])
                      ._encode_column(vs, header="val", cfg=DEFAULT_PIPELINE), None)
        linha["bN"] = B(c[0]) if c else None

        cands = {k: v for k, v in linha.items() if k in ROTS + ["spec_hoje", "bN"]
                 and isinstance(v, int) and linha.get(f"{k}_rt", True) is not False}
        hoje = {k: v for k, v in cands.items() if k in ("nucleo", "spec_hoje", "bN")}
        venc = min(cands, key=cands.get)
        venc_hoje = min(hoje, key=hoje.get)
        linha["vencedor_todos"] = venc
        linha["min_todos"] = cands[venc]
        linha["vencedor_hoje"] = venc_hoje
        linha["min_hoje"] = hoje[venc_hoje]
        linha["perda_hoje_pct"] = round(100 * (1 - cands[venc] / hoje[venc_hoje]), 1)
        reg.append(linha)
        _js(OUT / f"{nome}.meta.json", linha)
        cel = " ".join(f"{(linha[r] if isinstance(linha[r], int) else '—'):>11}" for r in ROTS)
        print(f"  {nome:>21} {cel} | {linha['spec_hoje']:>10} "
              f"{str(linha['bN'] or '—'):>7} | {cands[venc]:>10} {linha['perda_hoje_pct']:>9.1f}%")

    print(f"\n  vencedores (min de TODOS):")
    from collections import Counter
    for k, v in Counter(r["vencedor_todos"] for r in reg).most_common():
        print(f"    {k:>14}: {v} de {len(reg)} regimes")
    ganhos = [r for r in reg if r["perda_hoje_pct"] > 0]
    print(f"\n  regimes em que um candidato NOVO bateria o melhor de hoje: "
          f"{len(ganhos)} de {len(reg)}")
    for r in sorted(ganhos, key=lambda x: -x["perda_hoje_pct"])[:6]:
        print(f"    {r['regime']:>21}: {r['min_hoje']:>6} -> {r['min_todos']:>6} B "
              f"({r['perda_hoje_pct']:>5.1f}%) via {r['vencedor_todos']}")

    _js(INT / "candidatos.json", reg)
    _js(RAIZ / "resultado.json", {"regimes": reg, "falhas": falhas})
    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — date: o processo de compressão", "",
         "Cada `<regime>.<transformacao>.tcf` é o wire daquele candidato **isolado**.",
         "`<regime>.spec-welded.tcf` é o que o TCF emite hoje.", "",
         "| regime | n | k | hoje | min(todos) | vencedor | ganho |",
         "|---|---|---|---|---|---|---|"] +
        [f"| [`{r['regime']}`](./{r['regime']}.spec-welded.tcf) | {r['n']} | {r['distintos']} | "
         f"{r['min_hoje']} | {r['min_todos']} | **{r['vencedor_todos']}** | "
         f"{r['perda_hoje_pct']}% |" for r in reg]) + "\n")

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:15]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
