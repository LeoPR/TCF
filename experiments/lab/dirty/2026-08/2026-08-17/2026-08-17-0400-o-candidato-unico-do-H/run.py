"""O `.8H` perde +23% no corpus. É MESMO o candidato único que explica?

A PERGUNTA (uma só)
-------------------
O `.8M` roda `min(tcf, raw, dict, split)` por coluna (`multi/core.py:457`).
O `.8H` chama `_encode_col(...)` direto (`hierarchical.py:491,496,502`) — o encoder
SINGLE-COL, que tem os candidatos DELE (polaridade, denso, bN, nature) mas NÃO tem
`raw`/`dict`/`split`.

Se o gap `.8H − .8M` for explicado pela diferença **por coluna** entre
"o que o single-col dá" e "o que o min() do M daria", então o header do `.8H`
está encerrado como assunto: o trabalho é ABRIR O `min()` nas folhas.

Se NÃO fechar, sobra algo que eu não vi, e aí o header volta pra mesa.

POR QUE ISSO PRECISA SER MEDIDO DE NOVO
---------------------------------------
O número dos +23% e o "99,99% explicado pelo candidato único" saíram de UMA
medição minha (lab 2026-08-16-2230). O owner pediu confirmação antes de gastar
esforço em cima. Esta é a contraprova, com o dado real e a decomposição explícita.

MÉTODO
------
Para cada tabela do corpus (janela CONTÍGUA do meio — a régua do lab 0530):
  1. `wire_M`  = encode(dict)                -> rota `.8M`, min() por coluna
  2. `wire_H`  = encode(list[dict])          -> rota `.8H`, candidato único
  3. Por coluna: `b_single` = len(encode(col, stamp=False))
                 `b_min`    = o menor entre os candidatos do M para AQUELA coluna
     O "orçamento" do candidato único é `sum(b_single − b_min)`.
  4. Comparar: `gap_real = B(wire_H) − B(wire_M)` contra o orçamento.

Round-trip validado nos DOIS wires antes de qualquer byte ser reportado (§RT).
`src/tcf` INTOCADO. Lê `Z:/tcf-data/` somente-leitura; NADA é baixado.
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))

OUT = AQUI / "outputs"
IN = AQUI / "inputs"
for d in (OUT, IN):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                          # noqa: E402
from tcf.multi.core import _fallback_safe               # noqa: E402
from tcf.multi.dict_v2b import _v2b_encode              # noqa: E402
from tcf.multi.split import _struct_split_encode        # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE                # noqa: E402

N_ALVO = 2000
CFG = DEFAULT_PIPELINE   # o MESMO default do `_encode_multi`


def B(t: str) -> int:
    return len(t.encode("utf-8"))


def min_do_M(vals: list[str]) -> tuple[int, str]:
    """Reimplementa `_best_of` de `multi/core.py:456-470` — que e' CLOSURE de
    `_encode_multi` e por isso nao da' pra importar. MESMA ordem e MESMO criterio
    (`<`, nao `<=`), pra que o empate resolva pro mesmo lado que o encoder real.

    Devolve (bytes_do_corpo, modo_vencedor).
    """
    tcf_body = encode(vals, stamp=False).encode("utf-8")
    bb, bm = tcf_body, "tcf"
    if _fallback_safe(vals):
        rb = "\n".join(vals).encode("utf-8")
        if len(rb) < len(bb):
            bb, bm = rb, "raw"
    vb = _v2b_encode(vals, cfg=CFG, min_len=None)
    if vb is not None and len(vb) < len(bb):
        bb, bm = vb, "dict"
    sb = _struct_split_encode(vals, cfg=CFG, min_len=None)
    if sb is not None and len(sb) < len(bb):
        bb, bm = sb, "split"
    return len(bb), bm


def tabelas_do_corpus():
    for db in sorted(glob.glob("Z:/tcf-data/interim/*.db")):
        if os.path.getsize(db) == 0:
            continue
        nome_db = os.path.basename(db)[:-3]
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            ts = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]
            for t in ts:
                n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                if n == 0:
                    continue
                off = max(0, (n - N_ALVO) // 2)
                cur = con.execute(f"SELECT * FROM {t} LIMIT {N_ALVO} OFFSET {off}")
                cols = [d[0] for d in cur.description]
                linhas = cur.fetchall()
                tab = {c: [("" if r[i] is None else str(r[i])) for r in linhas]
                       for i, c in enumerate(cols)}
                yield nome_db, t, tab
            con.close()
        except Exception as e:
            print(f"  !! {nome_db}: {type(e).__name__}: {e}")


def como_lista_de_dicts(tab: dict[str, list[str]]) -> list[dict]:
    """dict-de-colunas -> list[dict], que e' a forma que roteia pro `.8H`."""
    nomes = list(tab)
    n = len(tab[nomes[0]])
    return [{c: tab[c][i] for c in nomes} for i in range(n)]


def main() -> int:
    print("=" * 78)
    print("O CANDIDATO UNICO DO .8H — contraprova no corpus real")
    print("=" * 78)

    linhas: list[dict] = []
    for nome_db, t, tab in tabelas_do_corpus():
        rot = f"{nome_db}.{t}"
        try:
            wire_M = encode(tab)
            if decode(wire_M) != tab:                       # §RT: sem RT, sem byte
                print(f"  [PULA] {rot}: RT do .8M falhou")
                continue

            ds = como_lista_de_dicts(tab)
            wire_H = encode(ds)
            if decode(wire_H) != ds:
                print(f"  [PULA] {rot}: RT do .8H falhou")
                continue
            if not wire_H.startswith("#TCF.8H"):
                print(f"  [PULA] {rot}: nao roteou pro .8H ({wire_H.splitlines()[0][:24]!r})")
                continue
        except Exception as e:
            print(f"  [PULA] {rot}: {type(e).__name__}: {str(e)[:60]}")
            continue

        # decomposicao POR COLUNA
        orcamento = 0
        detalhe = []
        for c, vals in tab.items():
            b_single = B(encode(vals, stamp=False))         # o que a folha do .8H usa
            try:
                b_min, modo = min_do_M(vals)                # o min() do .8M
            except Exception:
                b_min, modo = b_single, "?"
            orcamento += b_single - b_min
            detalhe.append({"col": c, "single": b_single, "min": b_min,
                            "modo_min": modo, "delta": b_single - b_min})

        bM, bH = B(wire_M), B(wire_H)
        gap = bH - bM
        explicado = (orcamento / gap * 100) if gap else float("nan")
        linhas.append({
            "tabela": rot, "n_linhas": len(tab[list(tab)[0]]), "n_cols": len(tab),
            "bytes_M": bM, "bytes_H": bH, "gap": gap,
            "orcamento_candidato_unico": orcamento,
            "pct_explicado": explicado,
            "header_H": B(wire_H.split("\n", 1)[0]),
            "detalhe": detalhe,
        })
        print(f"  {rot[:38]:38} M={bM:7} H={bH:7} gap={gap:+7} "
              f"orcam={orcamento:+7} explica={explicado:6.1f}%")

        # evidencia em disco
        safe = rot.replace("/", "_")
        (IN / f"{safe}.json").write_text(
            json.dumps({k: v[:5] for k, v in tab.items()}, ensure_ascii=False, indent=1),
            encoding="utf-8", newline="")
        (OUT / f"{safe}.8M.tcf").write_text(wire_M, encoding="utf-8", newline="")
        (OUT / f"{safe}.8H.tcf").write_text(wire_H, encoding="utf-8", newline="")

    if not linhas:
        print("\nSEM CORPUS: Z:/tcf-data/interim/ inacessivel — NADA medido.")
        return 1

    tot_M = sum(x["bytes_M"] for x in linhas)
    tot_H = sum(x["bytes_H"] for x in linhas)
    tot_gap = tot_H - tot_M
    tot_orc = sum(x["orcamento_candidato_unico"] for x in linhas)
    tot_hdr = sum(x["header_H"] for x in linhas)

    print()
    print("=" * 78)
    print(f"tabelas medidas          : {len(linhas)}")
    print(f"total .8M                : {tot_M:>10} B")
    print(f"total .8H                : {tot_H:>10} B   ({(tot_H/tot_M-1)*100:+.1f}%)")
    print(f"GAP (H - M)              : {tot_gap:>+10} B")
    print(f"orcamento candidato unico: {tot_orc:>+10} B   "
          f"=> explica {tot_orc/tot_gap*100:.1f}% do gap")
    print(f"header do .8H (total)    : {tot_hdr:>10} B   "
          f"= {tot_hdr/tot_H*100:.2f}% do wire H, {tot_hdr/tot_gap*100:.1f}% do gap")
    print("=" * 78)

    (AQUI / "resultado.json").write_text(
        json.dumps({
            "origem": "Z:/tcf-data/interim/*.db (somente leitura; NADA baixado)",
            "regua": "janela CONTIGUA do meio, N_ALVO=2000 (lab 0530)",
            "total": {"tabelas": len(linhas), "bytes_M": tot_M, "bytes_H": tot_H,
                      "gap": tot_gap, "orcamento": tot_orc,
                      "pct_explicado": tot_orc / tot_gap * 100 if tot_gap else None,
                      "header_H": tot_hdr},
            "por_tabela": linhas,
        }, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    print(f"-> {AQUI / 'resultado.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
