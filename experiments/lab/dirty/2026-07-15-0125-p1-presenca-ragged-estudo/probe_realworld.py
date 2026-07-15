"""PW3 — probe REAL-WORLD do P1 (auditoria: anti-incidente 2026-05-21 exige dado real).

Fonte real: Z:/tcf-data/interim/receita-cnpj.db. `nome_fantasia` é null em ~48% dos
estabelecimentos. Serialização de API típica OMITE campos null → objeto RAGGED real (a chave
não está no dict, não é null). Aninha matriz→filiais e testa RT byte-exato pelo CORE weldado.
Zero mudança em src/tcf (API pública read-only)."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / "src"))
from tcf import decode, encode_hierarchical  # noqa: E402

HUB = Path("Z:/tcf-data/interim/receita-cnpj.db")


def main():
    if not HUB.exists():
        print("hub ausente — requires_data."); return
    con = sqlite3.connect(str(HUB)); con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT cnpj, matriz_filial, situacao, uf, nome_fantasia FROM estabelecimentos")]
    groups: dict = {}
    for r in rows:
        groups.setdefault(r["cnpj"][:8], []).append(r)

    def est(e):
        d = {"cnpj": str(e["cnpj"]), "mf": str(e["matriz_filial"]),
             "sit": str(e["situacao"]), "uf": str(e["uf"])}
        if e["nome_fantasia"] is not None:            # OMITE quando null (ragged real, API-style)
            d["fantasia"] = str(e["nome_fantasia"])
        return d

    docs = [{"raiz": raiz, "estabelecimentos": [est(e) for e in sorted(groups[raiz], key=lambda x: x["cnpj"])]}
            for raiz in sorted(groups)]
    n_total = sum(len(d["estabelecimentos"]) for d in docs)
    n_com = sum(1 for d in docs for e in d["estabelecimentos"] if "fantasia" in e)
    n_sem = n_total - n_com

    blob = encode_hierarchical(docs)
    ok = decode(blob) == docs
    has_opt = "?" in blob.split("\n", 1)[0]

    out = ["PW3 — P1 em DADO REAL (receita-cnpj, fantasia omitida quando null = ragged real)", "",
           f"  {len(docs)} raízes · {n_total} estabelecimentos · fantasia PRESENTE {n_com} / AUSENTE {n_sem}",
           f"  header tem campo opcional ('?'): {has_opt}",
           f"  RT byte-exato decode(encode_hierarchical)==docs: {ok}",
           f"  bytes .tcf: {len(blob.encode())}", "",
           "  → P1 (chave opcional) faz RT em dado REAL não-sintético com opcionalidade genuína",
           "    (não construída pra testar) — fecha o gate anti-incidente 2026-05-21 pro P1."]
    (HERE / "outputs" / "04-probe-realworld.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))
    con.close()
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
