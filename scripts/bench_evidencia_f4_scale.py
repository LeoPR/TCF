"""F4-ESCALA — RT byte-exato em POPULAÇÃO INTEIRA de TODOS os hubs prontos (2026-07-17).

Objetivo (owner): "se o `.8` rodar com tudo, fica de evidência de não ter erro" — o `.9` mexe
no código partindo de um baseline sabidamente verde. Este script roda a população COMPLETA de
cada tabela de cada hub pelo pipeline flat (encode→decode) e afirma RT byte-exato.

NÃO publica blob (dados reais efêmeros; só métrica). Complementa bench_evidencia_f4.py (amostral).
Hubs sem .db são pulados com nota (ex.: beijing-pm25 = bug de metadata pk:"No").

Saída: experiments/results/evidencia-0.8/f4/RESULT-SCALE.md
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from _paths import interim_db  # noqa: E402
from dataset_reader import DatasetReader  # noqa: E402
from tcf import decode, encode  # noqa: E402

OUT = ROOT / "experiments/results/evidencia-0.8/f4"

# (dataset, [tabelas] ou None=todas). Só os com .db presente rodam.
HUBS = [
    ("adult-census", None),
    ("ibge-municipios", None),
    ("tpch-sf001", None),
    ("tpch-sf01", None),
    ("br-identidades", None),
    ("receita-cnpj", None),
    ("wine-quality", None),
    ("online-retail", None),
    ("beijing-pm25", None),   # provavelmente ausente (bug metadata pk); pulado com nota
]


def _to_str_cols(cols: dict) -> dict:
    """Coage p/ str como o encode flat faz (None->'' etc.) — o contrato do núcleo de strings."""
    out = {}
    for name, vals in cols.items():
        out[str(name)] = ["" if v is None else str(v) for v in vals]
    return out


def run_table(reader: DatasetReader, table: str, limit: int | None = None) -> dict:
    cols = _to_str_cols(reader.columns(table, limit=limit))
    n_rows = len(next(iter(cols.values()))) if cols else 0
    t0 = time.perf_counter()
    blob = encode(cols)
    t_enc = time.perf_counter() - t0
    t0 = time.perf_counter()
    back = decode(blob)
    t_dec = time.perf_counter() - t0
    rt = back == cols
    return {"table": table, "n_rows": n_rows, "n_cols": len(cols),
            "tcf_bytes": len(blob.encode("utf-8")), "rt": rt,
            "enc_s": round(t_enc, 2), "dec_s": round(t_dec, 2)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F4-escala: RT byte-exato em populacao inteira")
    ap.add_argument("--hub", help="roda so' este hub (smoke rapido antes da run cheia)")
    ap.add_argument("--limit", type=int, default=None,
                    help="max de linhas por tabela (smoke). Default: populacao INTEIRA.")
    args = ap.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)
    hubs = [(d, t) for d, t in HUBS if not args.hub or d == args.hub]
    if args.hub and not hubs:
        raise SystemExit(f"hub desconhecido: {args.hub!r} (opcoes: {[d for d, _ in HUBS]})")
    rows, skipped = [], []
    for ds, tables in hubs:
        if not interim_db(ds).exists():
            skipped.append((ds, "hub .db ausente"))
            continue
        try:
            reader = DatasetReader(ds)
            tlist = tables or reader.tables      # tables é @property (não método)
        except Exception as e:  # noqa: BLE001
            skipped.append((ds, f"{type(e).__name__}: {str(e)[:40]}"))
            continue
        for table in tlist:
            try:
                r = run_table(reader, table, limit=args.limit)
                r["dataset"] = ds
                rows.append(r)
                flag = "OK " if r["rt"] else "FALHA!!"
                print(f"  [{flag}] {ds}/{table}: {r['n_rows']} linhas × {r['n_cols']} cols "
                      f"-> {r['tcf_bytes']}B  RT={r['rt']}  ({r['enc_s']}s enc / {r['dec_s']}s dec)")
            except Exception as e:  # noqa: BLE001
                skipped.append((f"{ds}/{table}", f"{type(e).__name__}: {str(e)[:44]}"))
                print(f"  [ERRO] {ds}/{table}: {type(e).__name__}: {str(e)[:50]}")

    ok = sum(1 for r in rows if r["rt"])
    total_rows = sum(r["n_rows"] for r in rows)
    # NAO-EVIDENCIA: zero tabela medida nao e' sucesso. O `ok == len(rows)` de antes
    # dava 0 == 0 -> True e a run saia com exit 0 anunciando 0/0 (2026-07-19: os 9 hubs
    # erraram e ninguem viu). Falha alto, e o proprio RESULT diz que nao serve.
    vazio = not rows
    L = ["# F4-ESCALA — RT byte-exato em população inteira (gerado por bench_evidencia_f4_scale.py)",
         ""]
    if vazio:
        L += ["> ⚠️ **NÃO É EVIDÊNCIA — zero tabelas medidas.** Todos os hubs foram pulados",
              "> (ver lista abaixo). Corrija a infra e rode de novo.", ""]
    L += [f"**{ok}/{len(rows)} tabelas RT byte-exato** · {total_rows:,} linhas totais · "
          f"{len(rows)} tabelas de {len({r['dataset'] for r in rows})} hubs.", "",
         "| hub | tabela | linhas | cols | tcf_B | RT | enc_s | dec_s |",
         "|---|---|---:|---:|---:|:--:|---:|---:|"]
    for r in sorted(rows, key=lambda x: (x["dataset"], x["table"])):
        L.append(f"| {r['dataset']} | {r['table']} | {r['n_rows']:,} | {r['n_cols']} | "
                 f"{r['tcf_bytes']:,} | {'✅' if r['rt'] else '❌'} | {r['enc_s']} | {r['dec_s']} |")
    if skipped:
        L += ["", "## Pulados (não bloqueiam — infra)", ""]
        for ds, why in skipped:
            L.append(f"- `{ds}`: {why}")
    (OUT / "RESULT-SCALE.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n{ok}/{len(rows)} tabelas RT byte-exato · {total_rows:,} linhas · "
          f"{len(skipped)} pulados. -> {OUT / 'RESULT-SCALE.md'}")
    if vazio:
        print("ERRO: zero tabelas medidas — isto NAO e' evidencia.")
        return 2
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
