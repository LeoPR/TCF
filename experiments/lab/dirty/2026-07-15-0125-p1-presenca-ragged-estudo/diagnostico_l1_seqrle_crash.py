"""DIAGNÓSTICO (rodar DE DIA — encode 200k é lento) — crash L1 no probe real-world PW3.

CONTEXTO (2026-07-15, sessão a retomar): o probe PW3 (receita-cnpj matriz→filiais) crashou no
DECODE do L1 (compressor de coluna), NÃO no P1:
    syntax.py:734  refs.extend(range(int(a), int(b) + 1))   ValueError: int('') b vazio
    (seq-RLE range 'A..B' com B vazio — camada HCC/seq-RLE, ABAIXO do P1)

JÁ ESTABELECIDO (isolate.py/pinpoint.py, scratchpad — resultados abaixo):
  - Ambos P1(ragged) E não-P1(coerido) crasham IDÊNTICO → NÃO é bug do P1.
  - Colunas isoladas pelo L1: cnpj ordenado (200k) RT=True · raiz-prefixo8 (51536) RT=True ·
    fantasia não-null (104148) RT=True. Ou seja, as colunas testadas fazem RT sozinhas.
  - Suíte 684 passed; fuzz seedado (estruturas diversas) passa. P1 está correto.
  - ABERTO: qual coluna EM CONTEXTO (mf/uf/sit/est.count — não testadas isoladas) OU se é
    interação/exaustão no rebuild do decode hierárquico (regressão que EU introduzi nas
    validações do PW1?). Este script decide.

ESTE SCRIPT: bisseca a lista de raízes até o MENOR prefixo que crasha o decode hierárquico
completo, depois decodifica COLUNA-A-COLUNA e nomeia a culpada + dumpa o body. Se nenhuma
coluna crasha isolada → é interação/exaustão (olhar as validações que adicionei em
decode_hierarchical). Se uma coluna crasha → é bug pré-existente do L1 seq-RLE (registrar
como BUG do core, R0-class, e ajustar o probe PW3 pra não disparar).

PRÓXIMO (após este script apontar):
  (a) coluna → abrir tickets/BUG-SEQRLE-RANGE (repro mínimo daqui), fix separado no core (com
      aprovação + gate byte-canônico); PW3 usa colunas/ordem que não disparam; push do P1.
  (b) framing → consertar decode_hierarchical ANTES de push.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]      # .../TCF
sys.path.insert(0, str(ROOT / "src"))
import tcf.hierarchical as H                     # noqa: E402
from tcf.decoder import decode as dc            # noqa: E402

HUB = Path("Z:/tcf-data/interim/receita-cnpj.db")


def build(groups, keys):
    def est(e):
        return {"cnpj": str(e["cnpj"]), "mf": str(e["matriz_filial"]), "sit": str(e["situacao"]),
                "uf": str(e["uf"]),
                "fantasia": "" if e["nome_fantasia"] is None else str(e["nome_fantasia"])}
    return [{"raiz": k, "est": [est(e) for e in sorted(groups[k], key=lambda x: x["cnpj"])]}
            for k in keys]


def main():
    if not HUB.exists():
        print("hub ausente"); return
    con = sqlite3.connect(str(HUB)); con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT cnpj, matriz_filial, situacao, uf, nome_fantasia FROM estabelecimentos")]
    groups: dict = {}
    for r in rows:
        groups.setdefault(r["cnpj"][:8], []).append(r)
    allkeys = sorted(groups)

    def crashes(keys):
        try:
            dc(H.encode_hierarchical(build(groups, keys))); return False
        except Exception:
            return True

    if not crashes(allkeys):
        print("NAO crasha na pop inteira (bug pode ter sido corrigido?)"); return
    lo, hi = 1, len(allkeys)
    while lo < hi:
        mid = (lo + hi) // 2
        if crashes(allkeys[:mid]):
            hi = mid
        else:
            lo = mid + 1
    keys = allkeys[:lo]
    print(f"menor prefixo de raizes que crasha: {lo} (de {len(allkeys)})")

    docs = build(groups, keys)
    blob = H.encode_hierarchical(docs)
    line1 = blob.split("\n", 1)[0]
    schema, order = H._parse_meta(line1[len(H.MAGIC):])
    raw = blob[len(line1) + 1:].encode("utf-8")
    off = 0
    for path, kind, size in order:
        body = raw[off:].decode() if size is None else raw[off:off + size].decode()
        if size is not None:
            off += size
        try:
            _ = dc(body) if body else []
        except Exception as e:
            print(f"COLUNA CULPADA (bug L1 pré-existente): path={path} kind={kind} size={size}")
            print(f"  {type(e).__name__}: {e}")
            print(f"  body[:500]: {body[:500]!r}")
            return
    print("NENHUMA coluna crasha isolada → interação/EXAUSTÃO no rebuild "
          "(revisar as validações add. em decode_hierarchical — possível regressão do PW1)")


if __name__ == "__main__":
    main()
