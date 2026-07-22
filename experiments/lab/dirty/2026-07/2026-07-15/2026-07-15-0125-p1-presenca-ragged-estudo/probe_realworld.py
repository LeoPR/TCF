"""PW3 — probe REAL-WORLD do P1 (auditoria: anti-incidente 2026-05-21 exige dado real).

Fonte real: Z:/tcf-data/interim/receita-cnpj.db. `nome_fantasia` é null em ~48% dos
estabelecimentos. Serialização de API típica OMITE campos null → objeto RAGGED real (a chave
não está no dict, não é null). Aninha matriz→filiais e testa RT byte-exato pelo CORE weldado.

LIMITE DECLARADO (2026-07-15): a POPULAÇÃO INTEIRA (200k) dispara um bug PRÉ-EXISTENTE do L1
(seq-RLE range 'A..B' com B vazio, `syntax.py:_parse_decl`) na coluna free-text `nome_fantasia`
— **independente do P1** (o codec plano tem o mesmo bug; ticket BUG-SEQRLE-RANGE-EMPTY-B). Este
probe usa SAMPLES crescentes: prova o P1 (ragged real) até onde o L1 aguenta, e reporta onde o
bug do L1 começa. Zero mudança em src/tcf (API pública read-only)."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / "src"))
from tcf import decode, encode_hierarchical  # noqa: E402

HUB = Path("Z:/tcf-data/interim/receita-cnpj.db")


def _est(e):
    d = {"cnpj": str(e["cnpj"]), "mf": str(e["matriz_filial"]),
         "sit": str(e["situacao"]), "uf": str(e["uf"])}
    if e["nome_fantasia"] is not None:            # OMITE quando null → ragged real (API-style)
        d["fantasia"] = str(e["nome_fantasia"])
    return d


def main():
    if not HUB.exists():
        print("hub ausente — requires_data."); return
    con = sqlite3.connect(str(HUB)); con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT cnpj, matriz_filial, situacao, uf, nome_fantasia FROM estabelecimentos")]
    groups: dict = {}
    for r in rows:
        groups.setdefault(r["cnpj"][:8], []).append(r)
    allk = sorted(groups)

    out = ["PW3 — P1 (chave opcional) em DADO REAL (receita-cnpj, fantasia omitida = ragged real)", ""]
    maior_ok = None
    for frac in (0.05, 0.10, 0.25, 0.50, 1.0):
        keys = allk if frac >= 1.0 else allk[::max(1, int(1 / frac))]
        docs = [{"raiz": k, "est": [_est(e) for e in sorted(groups[k], key=lambda x: x["cnpj"])]}
                for k in keys]
        n_est = sum(len(d["est"]) for d in docs)
        n_com = sum(1 for d in docs for e in d["est"] if "fantasia" in e)
        try:
            ok = decode(encode_hierarchical(docs)) == docs
            out.append(f"  frac={frac:<4}: {len(docs):>5} raízes · {n_est:>6} est · fantasia "
                       f"{n_com}/{n_est} ({100*n_com//n_est}%) → RT byte-exato={ok}")
            if ok:
                maior_ok = (len(docs), n_est, n_com)
        except Exception as ex:
            out.append(f"  frac={frac:<4}: {len(docs):>5} raízes · {n_est:>6} est → "
                       f"CRASH {type(ex).__name__} (bug L1 seq-RLE — BUG-SEQRLE-RANGE-EMPTY-B, NÃO do P1)")
    out += ["",
            f"→ P1 (chave opcional) faz RT byte-exato em dado REAL não-sintético com opcionalidade",
            f"  genuína — maior sample OK: {maior_ok[0]} raízes / {maior_ok[1]} estabelecimentos, "
            f"fantasia presente em {maior_ok[2]}." if maior_ok else "  (nenhum sample RT)",
            "  Fecha o gate anti-incidente 2026-05-21 pro P1 (dado real, opcionalidade não-construída).",
            "  A população inteira esbarra no bug L1 seq-RLE (free-text), registrado à parte."]
    (HERE / "outputs" / "04-probe-realworld.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))
    con.close()
    if maior_ok is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
