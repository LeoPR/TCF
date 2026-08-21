"""TELEFONE BR REAL (Receita) — a lacuna declarada duas vezes, fechada.

O QUE ESTE LAB FECHA
--------------------
O levantamento `0900` mediu telefone só no TPC-H (`c_phone`, dbgen) e declarou:
*"o telefone 'real' é TPC-H, não BR — mesma classe, prova diferente"*. O lab `1200`
repetiu a lacuna. O dado BR real está pronto desde o perfil `enderecos`
(`ddd_1`/`telefone_1` da Receita Federal) e nunca foi medido.

TRÊS PERGUNTAS
--------------
  Q1  o −24,1% da nature (empacotamento de raiz) no `c_phone` TRANSFERE pro BR real?
  Q2  o dado BR já vem como GRUPO na origem (duas colunas) — juntar ajuda ou atrapalha?
  Q3  M4 do H-13-03: qual a taxa de dado SUJO real, e que forma ele tem?

A COLETA
--------
Shaper, `ShapeRequest(volume=20000, seed=42, stratify_by="uf")` — o MESMO request do
lab 1200 (padronização). Mix declarado. Comparações de estratégia no SUBCONJUNTO LIMPO
(ddd de 2 dígitos + fone de 8; 99,06%) — mascarar dado sujo criaria remonta falsa.
O sujo é medido à parte (Q3), não escondido.

AS FORMAS (baseline F0 = como a Receita entrega)
------------------------------------------------
  F0  duas colunas {ddd, fone}          <- a origem JÁ é grupo
  F1  uma coluna mascarada "(DD) FFFFFFFF"  <- como um app exportaria
  F2  uma coluna concatenada DDFFFFFFFF     <- 10 dígitos opacos
  F3  F0 + nature base85 no fone            <- grupo + empacotamento por campo
  F4  F2 + nature base85 nos 10 dígitos     <- opaco + empacotamento (o que o 0900 media)

Harness com as lições da sessão: `mede()` exige `remonta` (nada entra na tabela sem
prova de volta), evidência obrigatória por coluna, portão de completude no fim.
`src/tcf` INTOCADO. Nada baixado.
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

SEED, VOL = 42, 20000


def B(x):
    return len(x.encode("utf-8")) if isinstance(x, str) else len(x)


def min_do_M(vals):
    """`_best_of` de multi/core.py:456 (closure) — mesma ordem, mesmo critério."""
    bb, bm = encode(vals, stamp=False).encode("utf-8"), "tcf"
    if _fallback_safe(vals):
        rb = "\n".join(vals).encode("utf-8")
        if len(rb) < len(bb):
            bb, bm = rb, "raw"
    vb = _v2b_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if vb is not None and len(vb) < len(bb):
        bb, bm = vb, "dict"
    sb = _struct_split_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if sb is not None and len(sb) < len(bb):
        bb, bm = sb, "split"
    return len(bb), bm


def _slug(s):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in s)[:44]


def grava_evidencia(estrategia, nome_col, vals, bytes_rep, modo):
    """Wire REAL (.8M de 1 coluna) que decoda + meta — a licao do outputs/ vazio."""
    d = OUT / _slug(estrategia)
    d.mkdir(parents=True, exist_ok=True)
    tab = {nome_col: vals}
    wire = encode(tab)
    assert decode(wire) == tab, f"{estrategia}/{nome_col}: wire nao decoda"
    corpo = wire.split("\n", 1)[1].encode("utf-8")
    p = d / f"{_slug(nome_col)}.tcf"
    p.write_text(wire, encoding="utf-8", newline="")
    (d / f"{_slug(nome_col)}.roundtrip.json").write_text(
        json.dumps(decode(wire)[nome_col][:120], ensure_ascii=False),
        encoding="utf-8", newline="")
    (d / f"{_slug(nome_col)}.meta.json").write_text(json.dumps({
        "estrategia": estrategia, "coluna": nome_col, "n": len(vals),
        "distintos": len(set(vals)), "bytes_reportados": bytes_rep,
        "bytes_corpo": len(corpo), "modo": modo, "roundtrip": True,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    assert p.stat().st_size > 0
    return p


def mede(rot, colunas, original, *, remonta):
    """Bytes + PROVA de volta + evidência em disco. `remonta` é OBRIGATÓRIO."""
    total, det = 0, []
    for nome, vals in colunas.items():
        b, modo = min_do_M(vals)
        total += b
        pth = grava_evidencia(rot, nome, vals, b, modo)
        det.append({"col": nome, "bytes": b, "modo": modo,
                    "distintos": len(set(vals)),
                    "evidencia": str(pth.relative_to(AQUI)).replace("\\", "/")})
    volta = remonta(colunas)
    assert volta == original, f"{rot}: a remontagem NAO devolve o original"
    return {"estrategia": rot, "bytes": total, "colunas": det}


# ── a nature candidata: base85 de largura fixa, bijetiva ──────────────────
CHARSET = [chr(c) for c in range(33, 127) if c != 92][:85]      # sem '\'
IDX = {c: i for i, c in enumerate(CHARSET)}


def b85_fixo(digitos: str, largura: int) -> str:
    v = int(digitos)
    out = []
    for _ in range(largura):
        out.append(CHARSET[v % 85])
        v //= 85
    assert v == 0, f"largura {largura} insuficiente p/ {digitos!r}"
    return "".join(reversed(out))


def b85_volta(s: str, ndig: int) -> str:
    v = 0
    for ch in s:
        v = v * 85 + IDX[ch]
    return str(v).zfill(ndig)


def main():
    print("=" * 94)
    print(f"TELEFONE BR REAL — Receita, Shaper(volume={VOL}, seed={SEED}, stratify_by='uf')")
    print("=" * 94)

    r = Shaper().apply(ShapeRequest(dataset="receita-cnpj-enderecos", volume=VOL,
                                    seed=SEED, stratify_by="uf"))
    rows = r.tables[list(r.tables)[0]]
    pares_todos = [(x.get("ddd_1") or "", x.get("telefone_1") or "") for x in rows]

    # ── Q3 / M4: o dado sujo, medido e NÃO escondido ──
    sujos = [(d, f) for d, f in pares_todos if len(d) != 2 or len(f) != 8]
    formas_sujas = collections.Counter(f"ddd:{len(d)},fone:{len(f)}" for d, f in sujos)
    print(f"\nQ3/M4 — DADO SUJO: {len(sujos)}/{len(pares_todos)} "
          f"({len(sujos)/len(pares_todos)*100:.2f}%)")
    for forma, k in formas_sujas.most_common(6):
        print(f"   {forma:22} {k:>5}")
    print("   (sem fone de 9 dígitos na base — a Receita registra fixo/8)")

    limpos = [(d, f) for d, f in pares_todos
              if len(d) == 2 and d.isdigit() and len(f) == 8 and f.isdigit()]
    ddd = [d for d, _ in limpos]
    fone = [f for _, f in limpos]
    n = len(limpos)
    mix = collections.Counter(x["uf"] for x in rows if x.get("uf"))
    print(f"\nSUBCONJUNTO LIMPO (comparações): n={n:,} ({n/len(pares_todos)*100:.2f}%)")
    print(f"MIX: " + " · ".join(f"{u}:{c/len(rows)*100:.1f}%" for u, c in mix.most_common(6)))
    print(f"   ddd distintos: {len(set(ddd))}   fone distintos: {len(set(fone)):,} "
          f"({len(set(fone))/n*100:.1f}%)")

    masc = [f"({d}) {f}" for d, f in limpos]
    concat = [d + f for d, f in limpos]
    fone85 = [b85_fixo(f, 5) for f in fone]          # 8 díg -> 5 chars
    conc85 = [b85_fixo(c, 6) for c in concat]        # 10 díg -> 6 chars
    assert [b85_volta(x, 8) for x in fone85] == fone
    assert [b85_volta(x, 10) for x in conc85] == concat

    ests = [
        mede("F0 duas colunas (como a Receita entrega)",
             {"ddd": ddd, "fone": fone}, limpos,
             remonta=lambda k: list(zip(k["ddd"], k["fone"]))),
        mede("F1 mascarada (DD) FFFFFFFF",
             {"tel": masc}, masc,
             remonta=lambda k: list(k["tel"])),
        mede("F2 concatenada 10 digitos",
             {"tel": concat}, concat,
             remonta=lambda k: list(k["tel"])),
        mede("F3 grupo + nature b85 no fone",
             {"ddd": ddd, "fone85": fone85}, limpos,
             remonta=lambda k: [(d, b85_volta(x, 8))
                                for d, x in zip(k["ddd"], k["fone85"])]),
        mede("F4 opaco + nature b85 nos 10 dig",
             {"tel85": conc85}, limpos,
             remonta=lambda k: [(b85_volta(x, 10)[:2], b85_volta(x, 10)[2:])
                                for x in k["tel85"]]),
    ]

    base = ests[0]["bytes"]
    print(f"\n{'estrategia':44} {'bytes':>9} {'B/par':>7} {'vs F0':>8}  modos")
    print("-" * 94)
    for e in ests:
        modos = ",".join(f"{c['col']}:{c['modo']}" for c in e["colunas"])
        print(f"{e['estrategia']:44} {e['bytes']:>9,} {e['bytes']/n:>7.2f} "
              f"{(e['bytes']/base-1)*100:>+7.1f}%  {modos[:30]}")

    # Q1: a transferencia do TPC-H
    print(f"\nQ1 — TRANSFERE? No c_phone (TPC-H, lab 0900) a nature valia -24,1% sobre")
    print(f"     o split. Aqui, sobre o baseline da ORIGEM (F0):")
    f3, f4 = ests[3]["bytes"], ests[4]["bytes"]
    print(f"     F3 (grupo+nature) {(f3/base-1)*100:+.1f}%   F4 (opaco+nature) {(f4/base-1)*100:+.1f}%")

    (AQUI / "resultado.json").write_text(json.dumps({
        "coleta": f"Shaper volume={VOL} seed={SEED} stratify_by=uf",
        "mix": dict(mix.most_common()),
        "n_total": len(pares_todos), "n_limpo": n,
        "sujo": {"n": len(sujos), "pct": len(sujos)/len(pares_todos)*100,
                 "formas": dict(formas_sujas.most_common())},
        "ddd_distintos": len(set(ddd)), "fone_distintos": len(set(fone)),
        "estrategias": ests,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    (IN / "amostra.json").write_text(
        json.dumps([{"ddd": d, "fone": f} for d, f in limpos[:60]], ensure_ascii=False),
        encoding="utf-8", newline="")

    n_tcf = len(list(OUT.rglob("*.tcf")))
    n_rt = len(list(OUT.rglob("*.roundtrip.json")))
    n_cols = sum(len(e["colunas"]) for e in ests)
    assert n_tcf == n_cols and n_rt == n_cols, \
        f"EVIDENCIA INCOMPLETA: {n_tcf}/{n_rt} p/ {n_cols} colunas"
    print(f"\n-> resultado.json + {n_tcf} wires + {n_rt} roundtrips em outputs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
