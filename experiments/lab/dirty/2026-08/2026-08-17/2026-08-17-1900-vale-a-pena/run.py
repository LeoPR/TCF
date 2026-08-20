"""Vale a pena? — prevalência do split no corpus, e o que o grupo mudaria.

A PERGUNTA (owner, 2026-08-17)
------------------------------
*"no fim é só ver se vale a pena o esforço de fazer o split + header mostrando pra
recompor e quais mecanismos prontos + alguns ajustes são melhores de reusar."*

O que falta pra decidir NÃO é ganho por coluna (já medido: o grupo é menor que o
split atual em 4/4). É **PREVALÊNCIA**: quantas colunas do corpus o split de fato
VENCE — não onde ele apenas se aplica. Ganho grande em coluna rara não paga esforço.

TRÊS NÚMEROS QUE DECIDEM
------------------------
  P1  em quantas colunas o split APLICA (passa o gate)
  P2  em quantas ele VENCE o min() (é o modo emitido)
  P3  quanto o grupo mudaria nessas — e quanto isso é do total do corpus

COLETA pelo SHAPER (teste de massa), com o mix DECLARADO ao lado.
§RT em tudo. `src/tcf` INTOCADO.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

IN, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                                # noqa: E402
from tcf.multi.core import _fallback_safe                     # noqa: E402
from tcf.multi.dict_v2b import _v2b_encode                    # noqa: E402
from tcf.multi.split import _struct_split_encode              # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE                     # noqa: E402
from shaper import Shaper, ShapeRequest                       # noqa: E402

SEED, VOL = 42, 4000
DATASETS = ["adult-census", "br-identidades", "ibge-municipios", "online-retail",
            "receita-cnpj", "receita-cnpj-enderecos", "tpch-sf001", "tpch-sf01",
            "wine-quality"]


def B(x):
    return len(x.encode("utf-8")) if isinstance(x, str) else len(x)


def candidatos(vals):
    """Os 4 do min() por coluna, com o corpo de cada."""
    c = {"tcf": encode(vals, stamp=False).encode("utf-8")}
    if _fallback_safe(vals):
        c["raw"] = "\n".join(vals).encode("utf-8")
    vb = _v2b_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if vb is not None:
        c["dict"] = vb
    sb = _struct_split_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if sb is not None:
        c["split"] = sb
    return c


def melhor_sem_split(vals):
    c = candidatos(vals)
    c.pop("split", None)
    m = min(c, key=lambda k: len(c[k]))
    return len(c[m]), m


def parte_campo(v):
    seq, atual, dig = [], "", None
    for ch in v:
        d = ch.isdigit()
        if dig is None:
            dig, atual = d, ch
            continue
        if d != dig:
            seq.append((dig, atual)); atual, dig = ch, d
        else:
            atual += ch
    seq.append((dig, atual))
    partes, campos = ([""] if seq[0][0] else []), []
    for eh, tok in seq:
        (campos if eh else partes).append(tok)
    if seq[-1][0]:
        partes.append("")
    return partes, campos


def separa(vals):
    p0, c0 = parte_campo(vals[0])
    if len(c0) < 2:
        return None
    cols = [[] for _ in c0]
    for v in vals:
        p, c = parte_campo(v)
        if p != p0 or len(c) != len(c0):
            return None
        for k, tok in enumerate(c):
            cols[k].append(tok)
    return p0, cols


def corpo_grupo(cols):
    """O corpo do grupo = os corpos das N colunas, pelos candidatos que já existem."""
    tot = 0
    for c in cols:
        b, _m = melhor_sem_split(c)   # campo é dígito puro: split não recursa (ADR-0026)
        tot += b
    return tot


def main():
    print("=" * 96)
    print(f"VALE A PENA? — prevalência do split no corpus (Shaper, seed={SEED}, vol={VOL})")
    print("=" * 96)

    linhas, mix = [], {}
    for ds in DATASETS:
        try:
            r = Shaper().apply(ShapeRequest(dataset=ds, volume=VOL, seed=SEED))
        except Exception as e:
            print(f"  [pula] {ds}: {type(e).__name__}: {str(e)[:50]}")
            continue
        for tab, rows in r.tables.items():
            if not rows:
                continue
            mix[f"{ds}.{tab}"] = len(rows)
            cols = {k: [("" if x[k] is None else str(x[k])) for x in rows] for k in rows[0]}
            for nome, vals in cols.items():
                if not any(vals):
                    continue
                cand = candidatos(vals)
                vencedor = min(cand, key=lambda k: len(cand[k]))
                b_venc = len(cand[vencedor])
                aplica = "split" in cand
                venceu = vencedor == "split"
                reg = {"dataset": ds, "tabela": tab, "coluna": nome,
                       "n": len(vals), "distintos": len(set(vals)),
                       "vencedor": vencedor, "bytes": b_venc,
                       "split_aplica": aplica, "split_vence": venceu}
                if venceu:
                    g = separa(vals)
                    if g:
                        reg["grupo_bytes"] = corpo_grupo(g[1])
                        reg["nf"] = len(g[1])
                linhas.append(reg)

    n_col = len(linhas)
    aplica = [x for x in linhas if x["split_aplica"]]
    vence = [x for x in linhas if x["split_vence"]]
    total_corpus = sum(x["bytes"] for x in linhas)
    total_vence = sum(x["bytes"] for x in vence)

    print(f"\nMIX DECLARADO: {len(mix)} tabelas de {len(set(x['dataset'] for x in linhas))} datasets")
    print(f"  {', '.join(f'{k}={v}' for k, v in list(mix.items())[:6])}…")

    print("\n" + "=" * 96)
    print("P1/P2 — PREVALÊNCIA")
    print("=" * 96)
    print(f"  colunas medidas                    : {n_col:>6}")
    print(f"  split APLICA (passa o gate)        : {len(aplica):>6}  ({len(aplica)/n_col*100:>5.1f}%)")
    print(f"  split VENCE o min()                : {len(vence):>6}  ({len(vence)/n_col*100:>5.1f}%)")
    print(f"  bytes do corpus (soma dos vencedor): {total_corpus:>10,}")
    print(f"  bytes nas colunas com split        : {total_vence:>10,}  "
          f"({total_vence/total_corpus*100:>5.1f}% do corpus)")

    print("\n  quem vence, no geral:")
    for m, k in collections.Counter(x["vencedor"] for x in linhas).most_common():
        bs = sum(x["bytes"] for x in linhas if x["vencedor"] == m)
        print(f"    {m:6} {k:>4} colunas  {bs:>11,} B  ({bs/total_corpus*100:>5.1f}% dos bytes)")

    print("\n" + "=" * 96)
    print("P3 — O QUE O GRUPO MUDARIA nas colunas onde o split vence")
    print("=" * 96)
    com_g = [x for x in vence if "grupo_bytes" in x]
    if com_g:
        soma_split = sum(x["bytes"] for x in com_g)
        soma_grupo = sum(x["grupo_bytes"] for x in com_g)
        # o marcador: template + juncao. Medido no lab 1800: 9-11 B; uso 11 (pessimista)
        MARCADOR = 11
        soma_grupo_total = soma_grupo + MARCADOR * len(com_g)
        print(f"  colunas comparáveis        : {len(com_g)}")
        print(f"  hoje (slot split aninhado) : {soma_split:>11,} B")
        print(f"  grupo (corpo + marcador)   : {soma_grupo_total:>11,} B  "
              f"({(soma_grupo_total/soma_split-1)*100:+.2f}%)")
        print(f"  delta                      : {soma_grupo_total-soma_split:>+11,} B  "
              f"= {(soma_grupo_total-soma_split)/total_corpus*100:+.3f}% do corpus")
        print(f"\n  {'coluna':44} {'nf':>3} {'split':>9} {'grupo':>9} {'delta':>8}")
        for x in sorted(com_g, key=lambda z: z["bytes"], reverse=True)[:12]:
            rot = f"{x['dataset']}.{x['tabela']}.{x['coluna']}"[:44]
            gt = x["grupo_bytes"] + MARCADOR
            print(f"  {rot:44} {x.get('nf',0):>3} {x['bytes']:>9,} {gt:>9,} "
                  f"{gt-x['bytes']:>+8,}")

    (AQUI / "resultado.json").write_text(json.dumps({
        "coleta": f"Shaper volume={VOL} seed={SEED}",
        "mix_declarado": mix,
        "n_colunas": n_col, "split_aplica": len(aplica), "split_vence": len(vence),
        "bytes_corpus": total_corpus, "bytes_split": total_vence,
        "colunas": linhas,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="")

    # evidencia: os wires das 6 colunas onde o split mais pesa
    for x in sorted(vence, key=lambda z: z["bytes"], reverse=True)[:6]:
        r = Shaper().apply(ShapeRequest(dataset=x["dataset"], volume=VOL, seed=SEED))
        rows = r.tables[x["tabela"]]
        vals = [("" if v[x["coluna"]] is None else str(v[x["coluna"]])) for v in rows]
        w = encode({x["coluna"]: vals})
        assert decode(w) == {x["coluna"]: vals}
        cid = f"{x['dataset']}.{x['tabela']}.{x['coluna']}".replace("/", "_")
        (OUT / f"{cid}.tcf").write_text(w, encoding="utf-8", newline="")
        (OUT / f"{cid}.roundtrip.json").write_text(
            json.dumps(decode(w)[x["coluna"]][:100], ensure_ascii=False),
            encoding="utf-8", newline="")
    n_ev = len(list(OUT.glob("*.tcf")))
    assert n_ev > 0, "sem evidencia"
    print(f"\n-> resultado.json + {n_ev} wires (as colunas onde o split mais pesa)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
