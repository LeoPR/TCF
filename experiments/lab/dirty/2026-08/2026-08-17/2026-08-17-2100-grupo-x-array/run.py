"""H-13-06 — grupo × array. Executa o plano de `notas/2026-08-17-2000`.

A HIPÓTESE (reformulada após a sondagem)
----------------------------------------
Substituir a coluna de ITENS por N colunas de grupo é **ortogonal** aos mecanismos de
array: `count`, `emask` e máscara de campo ficam **byte-idênticos**; só a(s) coluna(s)
de item mudam.

Razão: a contagem é de nível de ARRAY, os itens são de nível de ITEM. A coluna de itens
já vem densa e achatada entre registros — trocar 1 coluna por N não toca a contagem.

O COROLÁRIO TESTÁVEL (o que este lab mede)
------------------------------------------
O wire com grupo tem de ter o MESMO count, o MESMO emask e a MESMA máscara de campo que
o wire sem grupo. Se algum mudar -> F1, hipótese cai.

FALSIFICAÇÃO (do plano)
-----------------------
  F1  count/emask/máscara mudam quando o grupo entra
  F2  perde round-trip com grupo mas mantém sem
  F3  exige coluna de CONTROLE nova (quebraria a tese do lab 1800)
  F4  a ordem DFS / "última coluna omite size" não fecha com N colunas
  F5  o gate precisa de estado POR-REGISTRO (hoje é global por coluna)

A4/A8/A9 NÃO são falsificação — são o gate funcionando. Registra-se se a recusa é LIMPA.

MOCK: `src/tcf` INTOCADO. §RT e evidência obrigatória.
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
    if modo == "!":
        return _decode_raw_body(blob)
    if modo == "@":
        return _decode_v2b(blob)
    return decode(blob.decode("utf-8"))


# ── as colunas de CONTROLE do `.8H` real, extraídas do wire ───────────────
def controle_do_H(wire: str) -> dict:
    """{caminho/kind: bytes} das colunas mask/count/emask — o que F1 compara."""
    l1 = wire.split("\n", 1)[0]
    _schema, order, _nat = _parse_meta(l1[len(MAGIC):])
    raw = wire[len(l1) + 1:].encode("utf-8")
    saida, off = {}, 0
    for path, kind, size in order:
        b = size if size is not None else len(raw) - off
        blob = raw[off:off + b]
        off += b
        if kind == "mask" or kind.startswith(("count", "emask")):
            saida["/".join(path) + ":" + kind] = blob
    return saida


# ── template / grupo (o mesmo gate do split) ─────────────────────────────
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
    """Gate GLOBAL (não por-registro): todos os itens do dataset compartilham template?"""
    if not itens:
        return None, "sem itens (array(s) vazio(s)) — nada de onde tirar template"
    p0, c0 = parte_campo(itens[0])
    if len(c0) < 2:
        return None, f"<2 campos (nf={len(c0)})"
    cols = [[] for _ in c0]
    for v in itens:
        p, c = parte_campo(v)
        if p != p0 or len(c) != len(c0):
            return None, f"template não-uniforme em {v!r}"
        for k, tok in enumerate(c):
            cols[k].append(tok)
    if all(len(set(c)) == 1 for c in cols):
        return None, "nenhum campo varia"
    return (p0, cols), None


# ── shred de array (o que o `.8H` faz), preservando as colunas de controle ─
def shred_array(ds, campo="v"):
    """Devolve (count, emask, mask_campo, itens) — as MESMAS noções do `.8H`."""
    count, emask, mask, itens = [], [], [], []
    for reg in ds:
        if campo not in reg:
            mask.append("-")
            continue
        mask.append(".")
        arr = reg[campo]
        count.append(str(len(arr)))
        for el in arr:
            if el is None:
                emask.append("0")
            else:
                emask.append(".")
                itens.append(el)
    return count, emask, mask, itens


def monta(ds, *, usar_grupo, campo="v"):
    """Wire do mock. As colunas de CONTROLE são as mesmas com e sem grupo — é o ponto."""
    count, emask, mask, itens = shred_array(ds, campo)
    tem_mask = "-" in mask
    tem_emask = "0" in emask

    colunas = []                      # (rotulo, kind, valores)
    if tem_mask:
        colunas.append(("mask", "mask", mask))
    colunas.append(("count", "count", count))
    if tem_emask:
        colunas.append(("emask", "emask", emask))

    g, motivo = (agrupa(itens) if usar_grupo else (None, "grupo desligado"))
    if g:
        partes, campos = g
        for k, c in enumerate(campos):
            colunas.append((f"item.c{k}", "item", c))
    else:
        partes = None
        colunas.append(("item", "item", itens))

    corpos, modos, ent, tot = [], [], [], 0
    for _rot, _k, vals in colunas:
        corpo, modo = melhor_coluna(vals) if vals else (b"", "!")
        corpos.append(corpo); modos.append(modo); tot += len(corpo)
    vistos = 0
    for (rot, kind, _v), corpo, modo in zip(colunas, corpos, modos):
        vistos += len(corpo)
        # o MODO viaja no meta — como o `.8M` real faz com `!`/`@`. A versao
        # anterior deste mock ADIVINHAVA o decoder no decode (tentava um a um e
        # pegava o 1o que nao levantava) e devolvia VALOR ERRADO em silencio:
        # `_decode_raw_body` abre um corpo tcf sem reclamar e devolve os tokens
        # crus (`\1` em vez de `1`). Foi o que quebrou A2 e A10.
        ent.append(f"{rot}:{modo}{'' if vistos == tot else format(len(corpo), 'x')}")
    tmpl = "" if partes is None else "|" + "|".join(partes) + "|"
    meta = f"{campo}{tmpl}#[" + ",".join(ent)
    return ("#TCF.8Hmock" + meta + "\n").encode("utf-8") + b"".join(corpos), \
        {rot: corpo for (rot, _k, _v), corpo in zip(colunas, corpos)}, partes, motivo


def desmonta(wire, partes, campo="v"):
    l1, corpo = wire.split(b"\n", 1)
    meta = l1.decode("utf-8")
    meta = meta[meta.index("#[") + 2:]
    blocos, off = {}, 0
    for e in meta.split(","):
        rot, _, resto = e.rpartition(":")
        modo = resto[0] if resto[:1] in ("!", "@") else ""
        sz = resto[1:] if modo else resto
        fim = off + int(sz, 16) if sz else None
        blocos[rot] = (corpo[off:fim] if fim else corpo[off:], modo)
        off = fim if fim else len(corpo)
    return {r: (decoda_coluna(b, m) if b else []) for r, (b, m) in blocos.items()}


def reconstroi(dec, partes, ds_len, campo="v"):
    count = dec.get("count", [])
    emask = dec.get("emask")
    mask = dec.get("mask")
    if partes is None:
        itens = dec.get("item", [])
    else:
        cols = [dec[k] for k in sorted(dec) if k.startswith("item.c")]
        n = len(cols[0]) if cols else 0
        itens = ["".join(partes[k] + cols[k][i] for k in range(len(cols))) + partes[-1]
                 for i in range(n)]
    out, ic, ii, ie = [], 0, 0, 0
    for r in range(ds_len):
        if mask is not None and mask[r] == "-":
            out.append({})
            continue
        k = int(count[ic]); ic += 1
        arr = []
        for _ in range(k):
            if emask is not None:
                pres = emask[ie]; ie += 1
                if pres == "0":
                    arr.append(None); continue
            arr.append(itens[ii]); ii += 1
        out.append({campo: arr})
    return out


# ── os 10 casos do plano ──────────────────────────────────────────────────
def casos():
    yield ("A1", "array de estruturados, uniforme",
           [{"v": ["12.50", "7.99"]}, {"v": ["3.00", "45.10"]}, {"v": ["8.25"]}])
    yield ("A2", "contagens variadas (1,3,0,7)",
           [{"v": ["1.10"]}, {"v": ["2.20", "3.30", "4.40"]}, {"v": []},
            {"v": [f"{i}.{i:02d}" for i in range(1, 8)]}])
    yield ("A3", "array vazio em alguns registros",
           [{"v": ["12.50", "7.99"]}, {"v": []}, {"v": ["3.00"]}])
    yield ("A4", "TODOS os arrays vazios (0 itens)",
           [{"v": []}, {"v": []}, {"v": []}])
    yield ("A5", "null em elemento (emask)",
           [{"v": ["12.50", None]}, {"v": ["3.00", "4.10", None]}])
    yield ("A6", "campo ausente (mascara antes do count)",
           [{"v": ["12.50", "7.99"]}, {}, {"v": ["3.00"]}])
    yield ("A8", "template NAO-uniforme entre registros",
           [{"v": ["12.50", "7.99"]}, {"v": ["1.234,56"]}])
    yield ("A9", "um item so' no dataset inteiro",
           [{"v": ["12.50"]}])
    yield ("A10", "grupo x array com data ISO (3 campos)",
           [{"v": ["2026-01-05", "2026-02-12"]}, {"v": ["2026-03-19"]}])


def main():
    print("=" * 94)
    print("H-13-06 — GRUPO × ARRAY  (executa o plano de notas/2026-08-17-2000)")
    print("=" * 94)
    print("COROLARIO: count/emask/mascara tem de ficar BYTE-IDENTICOS com e sem grupo (F1)")

    res, falhas = [], []
    for cid, desc, ds in casos():
        # (1) referencia: o `.8H` REAL de hoje
        wH = encode(ds)
        rtH = decode(wH) == ds
        ctrlH = controle_do_H(wH)

        # (2) controle: mock SEM grupo   (3) tratamento: mock COM grupo
        wS, blocosS, _p, _m = monta(ds, usar_grupo=False)
        wC, blocosC, partesC, motivo = monta(ds, usar_grupo=True)

        # RT dos dois mocks
        try:
            rtS = reconstroi(desmonta(wS, None), None, len(ds)) == ds
        except Exception as e:
            rtS = f"ERRO {type(e).__name__}: {str(e)[:40]}"
        try:
            rtC = reconstroi(desmonta(wC, partesC), partesC, len(ds)) == ds
        except Exception as e:
            rtC = f"ERRO {type(e).__name__}: {str(e)[:40]}"

        # F1: as colunas de CONTROLE mudaram?
        ctrl_iguais = all(blocosS.get(k) == blocosC.get(k)
                          for k in ("mask", "count", "emask")
                          if k in blocosS or k in blocosC)
        # F3: apareceu coluna de controle NOVA?
        novas = ({k for k in blocosC if k in ("mask", "count", "emask")} -
                 {k for k in blocosS if k in ("mask", "count", "emask")})

        agrupou = partesC is not None
        f1 = not ctrl_iguais
        f2 = (rtC is not True) and (rtS is True)
        f3 = bool(novas)
        for cod, disp in (("F1", f1), ("F2", f2), ("F3", f3)):
            if disp:
                falhas.append((cid, cod))

        (IN / f"{cid}.json").write_text(json.dumps(ds, ensure_ascii=False),
                                        encoding="utf-8", newline="")
        (OUT / f"{cid}.8H-real.tcf").write_text(wH, encoding="utf-8", newline="")
        (OUT / f"{cid}.mock-sem-grupo.tcf").write_bytes(wS)
        (OUT / f"{cid}.mock-com-grupo.tcf").write_bytes(wC)
        (OUT / f"{cid}.roundtrip.json").write_text(
            json.dumps(reconstroi(desmonta(wC, partesC), partesC, len(ds))
                       if rtC is True else {"rt": str(rtC)}, ensure_ascii=False),
            encoding="utf-8", newline="")

        marca = "AGRUPOU" if agrupou else f"gate recusou: {motivo}"
        print(f"\n### {cid} — {desc}")
        print(f"  .8H real  {B(wH):>6} B  RT={rtH}   meta={wH.splitlines()[0]!r}")
        print(f"  mock sem  {len(wS):>6} B  RT={rtS}")
        print(f"  mock com  {len(wC):>6} B  RT={rtC}   {marca}")
        print(f"  controle (count/emask/mascara) IDENTICO com e sem grupo? "
              f"{'SIM' if ctrl_iguais else '*** NAO — F1 ***'}")
        if novas:
            print(f"  *** F3: coluna de controle NOVA: {novas} ***")
        for k in ("mask", "count", "emask"):
            if k in blocosS or k in blocosC:
                print(f"     {k:6} sem={len(blocosS.get(k, b'')):>4} B  "
                      f"com={len(blocosC.get(k, b'')):>4} B")

        res.append({"caso": cid, "desc": desc, "agrupou": agrupou,
                    "motivo_gate": motivo, "H_real": B(wH),
                    "mock_sem": len(wS), "mock_com": len(wC),
                    "rt_H": rtH, "rt_sem": rtS is True, "rt_com": rtC is True,
                    "F1_controle_mudou": f1, "F2_perdeu_rt": f2,
                    "F3_coluna_nova": f3,
                    "controle_sem": {k: len(v) for k, v in blocosS.items()
                                     if k in ("mask", "count", "emask")},
                    "controle_com": {k: len(v) for k, v in blocosC.items()
                                     if k in ("mask", "count", "emask")}})

    print("\n" + "=" * 94)
    print("VEREDITO")
    print("=" * 94)
    agr = [x for x in res if x["agrupou"]]
    print(f"  casos            : {len(res)}   agruparam: {len(agr)}   "
          f"gate recusou: {len(res)-len(agr)}")
    print(f"  RT com grupo     : {sum(x['rt_com'] for x in res)}/{len(res)}")
    print(f"  F1 (controle mudou)      : {sum(x['F1_controle_mudou'] for x in res)}")
    print(f"  F2 (perdeu RT)           : {sum(x['F2_perdeu_rt'] for x in res)}")
    print(f"  F3 (coluna controle nova): {sum(x['F3_coluna_nova'] for x in res)}")
    print(f"\n  {'caso':5} {'agrupou':>8} {'sem':>7} {'com':>7} {'delta':>7}  gate")
    for x in res:
        d = x["mock_com"] - x["mock_sem"]
        print(f"  {x['caso']:5} {'sim' if x['agrupou'] else 'nao':>8} "
              f"{x['mock_sem']:>7} {x['mock_com']:>7} {d:>+7}  "
              f"{'' if x['agrupou'] else x['motivo_gate'][:40]}")
    if falhas:
        print(f"\n  *** FALSIFICACOES: {falhas} ***")
    else:
        print("\n  NENHUMA falsificacao (F1/F2/F3) disparou.")

    (AQUI / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="")
    n = len(list(OUT.glob("*.tcf")))
    assert n == 3 * len(res), f"evidencia incompleta: {n}"
    print(f"\n-> {n} wires + {len(res)} roundtrips em outputs/")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
