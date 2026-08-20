"""A7 + F4 — fecha o plano de `notas/2026-08-17-2000`.

O QUE FALTOU no lab 2100
------------------------
  A7  array-EM-array com grupo na folha (o mock cobria 1 nível só)  -> H-13-11
  F4  a ordem DFS / "última coluna omite size" com N colunas no lugar de 1
      (o mock 2100 usava ordem própria; F4 nunca foi exercitado)

A FORMA REAL (sondada antes de escrever)
----------------------------------------
    [{"v": [["12.50"], ["7.99","3.00"]]}]   ->   #TCF.8Hv#:3[#:6[

      v  count        size=3      <- nível 0: quantos sub-arrays por registro
      v  count1       size=6      <- nível 1: quantos itens por sub-array
      v  arr_scalars  size=None   <- os ITENS, e a ÚLTIMA coluna OMITE o size

Três níveis dão `count`, `count1`, `count2`, e só então os itens.

A HIPÓTESE, estendida a N níveis
--------------------------------
Cada `countK` vive no SEU nível; os itens vivem no nível mais fundo. Trocar a coluna de
itens por N colunas de grupo não toca contagem NENHUMA — de nenhum nível.

O QUE F4 TESTA, agora concretamente
-----------------------------------
Com 1 coluna de itens, ela é a última e omite o size. Com N colunas de grupo, a **última
das N** passa a omitir. A regra fecha? Se o decode não conseguir fatiar, F4 dispara.

MOCK: `src/tcf` INTOCADO. §RT e evidência obrigatória. O modo VIAJA no meta (a lição do
lab 2100: helper que adivinha decoder devolve valor errado em silêncio).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))

IN, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                                # noqa: E402
from tcf.multi.core import _fallback_safe, _decode_raw_body   # noqa: E402
from tcf.multi.dict_v2b import _v2b_encode, _decode_v2b       # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE                     # noqa: E402
from tcf.hierarchical import MAGIC, _parse_meta               # noqa: E402


def B(x):
    return len(x.encode("utf-8")) if isinstance(x, str) else len(x)


def melhor_coluna(vals):
    if not vals:
        return b"", "!"
    corpo, modo = encode(vals, stamp=False).encode("utf-8"), ""
    if _fallback_safe(vals):
        rb = "\n".join(vals).encode("utf-8")
        if len(rb) < len(corpo):
            corpo, modo = rb, "!"
    vb = _v2b_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if vb is not None and len(vb) < len(corpo):
        corpo, modo = vb, "@"
    return corpo, modo


def decoda_coluna(blob, modo):
    if not blob:
        return []
    if modo == "!":
        return _decode_raw_body(blob)
    if modo == "@":
        return _decode_v2b(blob)
    return decode(blob.decode("utf-8"))


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


def agrupa(itens):
    if not itens:
        return None, "sem itens"
    p0, c0 = parte_campo(itens[0])
    if len(c0) < 2:
        return None, f"<2 campos (nf={len(c0)})"
    cols = [[] for _ in c0]
    for v in itens:
        p, c = parte_campo(v)
        if p != p0 or len(c) != len(c0):
            return None, f"template nao-uniforme em {v!r}"
        for k, tok in enumerate(c):
            cols[k].append(tok)
    if all(len(set(c)) == 1 for c in cols):
        return None, "nenhum campo varia"
    return (p0, cols), None


# ── shred de array ANINHADO: um count por NIVEL, itens no fundo ──────────
def shred_nivel(ds, campo="v"):
    """Devolve ([count0, count1, ...], itens) na MESMA nocao do `.8H` real."""
    def prof(x):
        return 1 + prof(x[0]) if isinstance(x, list) and x and isinstance(x[0], list) else \
            (1 if isinstance(x, list) else 0)
    amostra = next((r[campo] for r in ds if campo in r and r[campo]), [])
    niveis = prof(amostra)
    counts = [[] for _ in range(niveis)]
    itens = []

    def anda(x, lvl):
        counts[lvl].append(str(len(x)))
        for el in x:
            if isinstance(el, list):
                anda(el, lvl + 1)
            else:
                itens.append(el)
    for r in ds:
        anda(r.get(campo, []), 0)
    return counts, itens, niveis


def monta(ds, *, usar_grupo, campo="v"):
    counts, itens, niveis = shred_nivel(ds, campo)
    colunas = [(f"count{k if k else ''}", c) for k, c in enumerate(counts)]

    g, motivo = (agrupa(itens) if usar_grupo else (None, "grupo desligado"))
    partes = None
    if g:
        partes, campos = g
        colunas += [(f"item.c{k}", c) for k, c in enumerate(campos)]
    else:
        colunas.append(("item", itens))

    corpos, modos = [], []
    for _rot, vals in colunas:
        c, m = melhor_coluna(vals)
        corpos.append(c); modos.append(m)

    # F4: a ULTIMA coluna omite o size — com grupo, a ultima das N.
    ent = []
    for i, ((rot, _v), corpo, modo) in enumerate(zip(colunas, corpos, modos)):
        ultima = (i == len(colunas) - 1)
        ent.append(f"{rot}:{modo}{'' if ultima else format(len(corpo), 'x')}")
    tmpl = "" if partes is None else "|" + "|".join(partes) + "|"
    meta = f"{campo}{tmpl}" + "#[" * niveis + ",".join(ent)
    return ("#TCF.8Hmock" + meta + "\n").encode("utf-8") + b"".join(corpos), \
        {r: c for (r, _v), c in zip(colunas, corpos)}, partes, niveis, motivo


def desmonta(wire, partes, niveis, campo="v"):
    l1, corpo = wire.split(b"\n", 1)
    meta = l1.decode("utf-8")
    meta = meta[meta.rindex("#[") + 2:]
    blocos, off = {}, 0
    for e in meta.split(","):
        rot, _, resto = e.rpartition(":")
        modo = resto[0] if resto[:1] in ("!", "@") else ""
        sz = resto[1:] if modo else resto
        fim = off + int(sz, 16) if sz else None            # F4: sem size -> ate' EOF
        blocos[rot] = (corpo[off:fim] if fim is not None else corpo[off:], modo)
        off = fim if fim is not None else len(corpo)
    return {r: decoda_coluna(b, m) for r, (b, m) in blocos.items()}


def reconstroi(dec, partes, niveis, ds_len, campo="v"):
    counts = [dec[f"count{k if k else ''}"] for k in range(niveis)]
    if partes is None:
        itens = dec["item"]
    else:
        cols = [dec[k] for k in sorted(dec) if k.startswith("item.c")]
        n = len(cols[0]) if cols else 0
        itens = ["".join(partes[k] + cols[k][i] for k in range(len(cols))) + partes[-1]
                 for i in range(n)]
    pos = [0] * niveis
    it = [0]

    def anda(lvl):
        k = int(counts[lvl][pos[lvl]]); pos[lvl] += 1
        out = []
        for _ in range(k):
            if lvl + 1 < niveis:
                out.append(anda(lvl + 1))
            else:
                out.append(itens[it[0]]); it[0] += 1
        return out
    return [{campo: anda(0)} for _ in range(ds_len)]


def casos():
    yield ("B1", "2 niveis, 1 registro",
           [{"v": [["12.50"], ["7.99", "3.00"]]}])
    yield ("B2", "2 niveis, 2 registros",
           [{"v": [["12.50", "7.99"]]}, {"v": [["3.00"], ["45.10", "8.25"]]}])
    yield ("B3", "2 niveis, sub-array VAZIO",
           [{"v": [[], ["7.99", "3.00"]]}])
    yield ("B4", "3 NIVEIS (count/count1/count2)",
           [{"v": [[["12.50"]], [["7.99", "3.00"]]]}])
    yield ("B5", "3 niveis, 2 registros, data ISO (3 campos)",
           [{"v": [[["2026-01-05"]], [["2026-02-12", "2026-03-19"]]]},
            {"v": [[["2026-04-01", "2026-05-08"]]]}])
    yield ("B6", "2 niveis, template nao-uniforme (gate)",
           [{"v": [["12.50"], ["1.234,56"]]}])


def main():
    print("=" * 92)
    print("A7 + F4 — array-EM-array com grupo na folha (fecha o plano de 2000)")
    print("=" * 92)

    res, falhas = [], []
    for cid, desc, ds in casos():
        wH = encode(ds); rtH = decode(wH) == ds
        l1H = wH.split("\n", 1)[0]
        _s, ordemH, _n = _parse_meta(l1H[len(MAGIC):])

        wS, blocosS, _p, nivS, _m = monta(ds, usar_grupo=False)
        wC, blocosC, partesC, nivC, motivo = monta(ds, usar_grupo=True)

        try:
            rtS = reconstroi(desmonta(wS, None, nivS), None, nivS, len(ds)) == ds
        except Exception as e:
            rtS = f"ERRO {type(e).__name__}: {str(e)[:38]}"
        try:
            rtC = reconstroi(desmonta(wC, partesC, nivC), partesC, nivC, len(ds)) == ds
        except Exception as e:
            rtC = f"ERRO {type(e).__name__}: {str(e)[:38]}"

        # F1 em TODOS os niveis de contagem
        chaves = [k for k in blocosS if k.startswith("count")]
        f1 = any(blocosS.get(k) != blocosC.get(k) for k in chaves)
        # F4: a ultima coluna omite size e o decode fecha?
        ult_sem_size = wC.split(b"\n")[0].decode("utf-8").rstrip().split(",")[-1]
        f4 = (rtC is not True)
        f2 = (rtC is not True) and (rtS is True)
        agrupou = partesC is not None
        for cod, d in (("F1", f1), ("F2", f2), ("F4", f4 and agrupou)):
            if d:
                falhas.append((cid, cod))

        (IN / f"{cid}.json").write_text(json.dumps(ds, ensure_ascii=False),
                                        encoding="utf-8", newline="")
        (OUT / f"{cid}.8H-real.tcf").write_text(wH, encoding="utf-8", newline="")
        (OUT / f"{cid}.mock-sem-grupo.tcf").write_bytes(wS)
        (OUT / f"{cid}.mock-com-grupo.tcf").write_bytes(wC)
        (OUT / f"{cid}.roundtrip.json").write_text(
            json.dumps(reconstroi(desmonta(wC, partesC, nivC), partesC, nivC, len(ds))
                       if rtC is True else {"rt": str(rtC)}, ensure_ascii=False),
            encoding="utf-8", newline="")

        print(f"\n### {cid} — {desc}   ({nivC} niveis)")
        print(f"  .8H real  {B(wH):>5} B  RT={rtH}   meta={l1H!r}")
        print(f"     colunas reais: {[(k, s) for _p2, k, s in ordemH]}")
        print(f"  mock sem  {len(wS):>5} B  RT={rtS}")
        print(f"  mock com  {len(wC):>5} B  RT={rtC}   "
              f"{'AGRUPOU' if agrupou else 'gate: ' + motivo}")
        print(f"  F1 (contagens de TODOS os niveis identicas)? "
              f"{'SIM' if not f1 else '*** NAO ***'}")
        for k in chaves:
            print(f"     {k:8} sem={len(blocosS.get(k, b'')):>3} B  com={len(blocosC.get(k, b'')):>3} B")
        print(f"  F4 (ultima coluna SEM size, decode fecha)? "
              f"{'SIM' if not (f4 and agrupou) else '*** NAO ***'}   ultima entrada: {ult_sem_size!r}")

        res.append({"caso": cid, "desc": desc, "niveis": nivC, "agrupou": agrupou,
                    "motivo": motivo, "H_real": B(wH), "sem": len(wS), "com": len(wC),
                    "rt_H": rtH, "rt_sem": rtS is True, "rt_com": rtC is True,
                    "F1": f1, "F2": f2, "F4": f4 and agrupou,
                    "ultima_entrada": ult_sem_size,
                    "counts_sem": {k: len(blocosS.get(k, b"")) for k in chaves},
                    "counts_com": {k: len(blocosC.get(k, b"")) for k in chaves}})

    print("\n" + "=" * 92)
    print("VEREDITO")
    print("=" * 92)
    agr = [x for x in res if x["agrupou"]]
    print(f"  casos: {len(res)}   agruparam: {len(agr)}   gate recusou: {len(res)-len(agr)}")
    print(f"  RT com grupo : {sum(x['rt_com'] for x in res)}/{len(res)}")
    print(f"  F1 (contagem mudou)          : {sum(x['F1'] for x in res)}")
    print(f"  F2 (perdeu RT)               : {sum(x['F2'] for x in res)}")
    print(f"  F4 (ultima-sem-size quebrou) : {sum(x['F4'] for x in res)}")
    print(f"\n  {'caso':5} {'niv':>4} {'agrup':>6} {'sem':>6} {'com':>6}  ultima entrada")
    for x in res:
        print(f"  {x['caso']:5} {x['niveis']:>4} {'sim' if x['agrupou'] else 'nao':>6} "
              f"{x['sem']:>6} {x['com']:>6}  {x['ultima_entrada']!r}")
    print(f"\n  {'NENHUMA falsificacao disparou.' if not falhas else '*** ' + str(falhas) + ' ***'}")

    (AQUI / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="")
    n = len(list(OUT.glob("*.tcf")))
    assert n == 3 * len(res), f"evidencia incompleta: {n}"
    print(f"\n-> {n} wires + {len(res)} roundtrips em outputs/")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
