"""PROBE ROI-7 da auditoria — receita-cnpj matriz→filiais: 1ª fonte hierárquica REAL não-sintética.

A auditoria criticou que TPC-H é in-class POR CONSTRUÇÃO (dbgen: fan-out uniforme, sem null).
receita-cnpj é o oposto: agrupamento real matriz+filiais por raiz-CNPJ com CAUDA PESADA
(max 396 estabelecimentos/raiz, avg 3.88, 29561 raízes multi) e NULLS REAIS (nome_fantasia
48% null). Dois probes:

  (1) TOPOLOGIA, população INTEIRA (51536 grupos, 200k folhas) — colunas enum/código (sem
      free-text), null-free por seleção de colunas. Testa a cauda pesada real no #count.
  (2) CONTEÚDO com null real — nome_fantasia incluído: (2a) null coerido a "" (declarado;
      contrato null = pro fim) numa amostra estratificada honesta por uf; (2b) null CRU
      passado ao codec → documenta o comportamento (str(None)='None' = coerção silenciosa
      de TIPO, achado conhecido H-TYPE-01; null real REFORÇA a decisão de contrato pro fim).

Zero mudança em src/tcf (API pública read-only).
"""
from __future__ import annotations

import random
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "src"))
from tcf import decode, encode_hierarchical  # noqa: E402

HUB = Path("Z:/tcf-data/interim/receita-cnpj.db")


def _s(v):
    return "" if v is None else str(v)


def main():
    if not HUB.exists():
        print("hub receita-cnpj ausente — requires_data."); return
    con = sqlite3.connect(str(HUB)); con.row_factory = sqlite3.Row
    out = ["PROBE receita-cnpj — matriz→filiais (fonte hierárquica REAL, cauda pesada + null real)", ""]

    rows = [dict(r) for r in con.execute(
        "SELECT cnpj, matriz_filial, situacao, uf, cnae_principal, nome_fantasia "
        "FROM estabelecimentos")]
    groups: dict = {}
    for r in rows:
        groups.setdefault(r["cnpj"][:8], []).append(r)

    # ---- (1) topologia, população inteira, colunas null-free ----
    docs = []
    for raiz in sorted(groups):
        ests = sorted(groups[raiz], key=lambda x: x["cnpj"])
        docs.append({"raiz": raiz,
                     "estabelecimentos": [{"cnpj": _s(e["cnpj"]), "mf": _s(e["matriz_filial"]),
                                           "sit": _s(e["situacao"]), "uf": _s(e["uf"]),
                                           "cnae": _s(e["cnae_principal"])} for e in ests]})
    fanouts = [len(d["estabelecimentos"]) for d in docs]
    ok1 = decode(encode_hierarchical(docs)) == docs
    out.append(f"(1) TOPOLOGIA pop. inteira: {len(docs)} raízes, {sum(fanouts)} estabelecimentos, "
               f"fan-out max={max(fanouts)} avg={sum(fanouts)/len(fanouts):.2f} — RT={ok1}")
    out.append("    cauda pesada REAL exercitada no #count (o regime que o TPC-H uniforme não tem).")

    # ---- (2a) conteúdo com null→"" (coerção declarada), amostra estratificada por uf ----
    rng = random.Random(20260715)
    by_uf: dict = {}
    for raiz, ests in groups.items():
        by_uf.setdefault(ests[0]["uf"], []).append(raiz)
    sample = []
    for uf in sorted(by_uf):
        raizes = sorted(by_uf[uf])
        k = max(1, round(len(raizes) * 0.05))            # 5% proporcional por uf (min 1)
        sample += rng.sample(raizes, min(k, len(raizes)))
    docs2 = []
    n_null = 0
    for raiz in sorted(sample):
        ests = sorted(groups[raiz], key=lambda x: x["cnpj"])
        n_null += sum(1 for e in ests if e["nome_fantasia"] is None)
        docs2.append({"raiz": raiz,
                      "estabelecimentos": [{"cnpj": _s(e["cnpj"]),
                                            "fantasia": _s(e["nome_fantasia"]),
                                            "uf": _s(e["uf"])} for e in ests]})
    ok2 = decode(encode_hierarchical(docs2)) == docs2
    out.append(f"(2a) CONTEÚDO c/ free-text real + null→'' (coerção DECLARADA): {len(docs2)} raízes "
               f"(5% estratificado por uf, 27 estratos), {n_null} nulls reais coeridos — RT={ok2}")

    # ---- (2b) null CRU (sem coerção): documenta o comportamento ----
    raw = [{"raiz": "x", "estabelecimentos": [{"f": None}]}]
    try:
        back = decode(encode_hierarchical(raw))
        got = ("COERÇÃO SILENCIOSA DE TIPO: str(None)='None' → decode devolve 'None' != None "
               f"(RT quebra por tipo; obtido={back!r})" if back != raw else "RT-OK (inesperado)")
    except Exception as e:  # noqa: BLE001
        got = f"fail-loud: {type(e).__name__}"
    out.append(f"(2b) null CRU no codec: {got}")
    out.append("     → achado CONHECIDO (H-TYPE-01: codec faz str(v); lossless só all-string).")
    out.append("     null real em 48% de nome_fantasia REFORÇA: o contrato null (pro fim, decisão")
    out.append("     do owner) é pré-requisito pra ingerir receita-cnpj SEM coerção declarada.")

    out += ["", "SÍNTESE: contenção 1:N em fonte REAL não-sintética com cauda pesada — RT byte-exato",
            "na população inteira (topologia) e na amostra honesta com free-text+null-coerido.",
            "Null cru segue fora da classe coberta (coerção de tipo documentada, não silenciada)."]
    text = "\n".join(out) + "\n"
    (HERE / "outputs" / "03-probe-receita.txt").write_bytes(text.encode("utf-8"))
    print(text)
    if not (ok1 and ok2):
        sys.exit(1)


if __name__ == "__main__":
    main()
