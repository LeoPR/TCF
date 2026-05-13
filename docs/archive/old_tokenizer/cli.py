import os
import argparse
from typing import Optional
from .schema import load_metadata, load_tables
from .vocab import fit_artifacts, save_artifacts, load_artifacts
from .encode import encode_tables, save_tokens_jsonl
from .report import compute_stats, save_report, print_summary


def cmd_fit(args: argparse.Namespace) -> None:
    meta = load_metadata(args.metadata)
    tables, _ = load_tables(os.getcwd(), meta)
    artifacts = fit_artifacts(tables, n_bins=args.n_bins)
    save_artifacts(artifacts, args.artifacts)
    print(f"OK: artefatos salvos em {args.artifacts}")


def cmd_encode(args: argparse.Namespace) -> None:
    meta = load_metadata(args.metadata)
    tables, _ = load_tables(os.getcwd(), meta)
    artifacts = load_artifacts(args.artifacts)
    encoded = encode_tables(tables, artifacts)
    save_tokens_jsonl(encoded, args.output)
    print(f"OK: tokens salvos em {args.output}")


def cmd_report(args: argparse.Namespace) -> None:
    meta = load_metadata(args.metadata)
    tables, _ = load_tables(os.getcwd(), meta)
    artifacts = load_artifacts(args.artifacts)
    stats = compute_stats(tables, artifacts)
    save_report(stats, args.output)
    print_summary(stats)
    print(f"\nRelatório completo salvo em {args.output}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Tokenizer compacto para dados")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_fit = sub.add_parser("fit", help="Ajusta vocabulários/bins e salva artefatos")
    p_fit.add_argument("--metadata", default="metadata.json", help="Caminho para metadata.json")
    p_fit.add_argument("--n-bins", type=int, default=16, help="Nº de bins para colunas numéricas")
    p_fit.add_argument("--artifacts", default="artifacts", help="Pasta para salvar artefatos")
    p_fit.set_defaults(func=cmd_fit)

    p_enc = sub.add_parser("encode", help="Tokeniza dados usando artefatos salvos")
    p_enc.add_argument("--metadata", default="metadata.json", help="Caminho para metadata.json")
    p_enc.add_argument("--artifacts", default="artifacts", help="Pasta com artefatos")
    p_enc.add_argument("--output", default="tokens", help="Pasta de saída para tokens")
    p_enc.set_defaults(func=cmd_encode)

    p_rep = sub.add_parser("report", help="Gera estatísticas de vocabulário, cobertura e bins")
    p_rep.add_argument("--metadata", default="metadata.json", help="Caminho para metadata.json")
    p_rep.add_argument("--artifacts", default="artifacts", help="Pasta com artefatos")
    p_rep.add_argument("--output", default="artifacts/report.json", help="Arquivo de saída para relatório")
    p_rep.set_defaults(func=cmd_report)

    return p


def main(argv: Optional[list] = None) -> None:
    p = build_parser()
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
