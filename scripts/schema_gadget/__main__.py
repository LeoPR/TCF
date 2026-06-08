"""CLI do schema/quality gadget — Fase 4.

ALERT-ONLY: analisa um dataset e emite relatório. NUNCA modifica nada.

Uso:
    python -m schema_gadget analyze <dataset>            # markdown no stdout
    python -m schema_gadget analyze <dataset> --json     # JSON
    python -m schema_gadget analyze tpch-sf001 --rows 5000 --fk-confidence alta
    python -m schema_gadget list                         # hubs disponíveis em Z:

(rodar de dentro de scripts/, ou: python scripts/schema_gadget/__main__.py ...)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Permite rodar tanto como módulo (-m schema_gadget) quanto direto.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/
if __package__:
    from .report import analyze_dataset
else:  # execução direta do arquivo
    from report import analyze_dataset


def _list_hubs() -> list[str]:
    from _paths import data_root
    interim = data_root() / "interim"
    if not interim.exists():
        return []
    return sorted(f.stem for f in interim.glob("*.db"))


def _fk_to_dict(fk) -> dict:
    return {
        "child": f"{fk.child_table}.{fk.child_col}",
        "parent": f"{fk.parent_table}.{fk.parent_col}",
        "overlap": fk.overlap,
        "n_orphans": fk.n_orphans,
        "confidence": fk.confidence,
        "is_clean": fk.is_clean,
    }


def _alert_to_dict(a) -> dict:
    return {"column": a.column, "kind": a.kind,
            "severity": a.severity, "detail": a.detail}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="schema_gadget",
        description="Análise de schema/qualidade (ALERT-ONLY — nunca modifica dados).",
    )
    sub = ap.add_subparsers(dest="cmd")

    ap_an = sub.add_parser("analyze", help="analisa um dataset do hub")
    ap_an.add_argument("dataset", help="nome do dataset (ver `list`)")
    ap_an.add_argument("--json", action="store_true", help="saída JSON em vez de markdown")
    ap_an.add_argument("--rows", type=int, default=20000,
                       help="máx. linhas por tabela (default 20000; 0 = todas)")
    ap_an.add_argument("--fk-confidence", default="media",
                       choices=["baixa", "media", "alta"],
                       help="confiança mínima dos FK candidates (default media)")

    sub.add_parser("list", help="lista datasets (hubs SQLite em Z:)")

    args = ap.parse_args(argv)

    if args.cmd == "list":
        hubs = _list_hubs()
        if hubs:
            print("Datasets disponíveis (hubs em Z:/tcf-data/interim/):")
            for h in hubs:
                print(f"  {h}")
        else:
            print("Nenhum hub encontrado em Z:/tcf-data/interim/.")
        return 0

    if args.cmd == "analyze":
        try:
            rep = analyze_dataset(
                args.dataset,
                row_limit=(None if args.rows == 0 else args.rows),
                fk_min_confidence=args.fk_confidence,
            )
        except FileNotFoundError as e:
            print(f"erro: {e}", file=sys.stderr)
            print(f"(use `python -m schema_gadget list` para ver datasets)", file=sys.stderr)
            return 2

        if args.json:
            out = {
                "dataset": args.dataset,
                "counts": rep["counts"],
                "fks": [_fk_to_dict(fk) for fk in rep["fks"]],
                "quality": {t: [_alert_to_dict(a) for a in al]
                            for t, al in rep["quality"].items()},
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            print(rep["markdown"])
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
