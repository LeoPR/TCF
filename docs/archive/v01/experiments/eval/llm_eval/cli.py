import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Iterable

from . import chunker
from .runner import run_questions_over_chunks, save_results
from .metrics import score_results, save_report
from .formats import list_formats
from .models import fetch_local_models, rank_models, save_models, auto_select_models
from .aggregator import consolidate, save_consolidated


def _iter_chunks(rows: List[Dict[str, Any]], table: str, rows_per_chunk: int) -> Iterable[Tuple[str, List[Dict[str, Any]]]]:
    chunks = chunker.chunk_rows(rows, rows_per_chunk=rows_per_chunk)
    for i, ch in enumerate(chunks):
        yield (f"{table}:{i:04d}", ch)


def _compute_ground_truth(chunks: Iterable[Tuple[str, List[Dict[str, Any]]]], sum_field: str | None) -> Dict[str, Dict[str, Any]]:
    gt: Dict[str, Dict[str, Any]] = {}
    for cid, rows in chunks:
        # We consume; but caller may need chunks again. So rebuild list per iteration.
        count = len(rows)
        row_sum = None
        if sum_field:
            acc = 0.0
            for r in rows:
                v = r.get(sum_field)
                try:
                    if v is not None:
                        acc += float(str(v).replace(',', '.'))
                except Exception:
                    pass
            row_sum = acc
        gt[cid] = {"count_rows": count}
        if row_sum is not None:
            gt[cid]["sum_field"] = row_sum
    return gt


def cmd_eval(args: argparse.Namespace) -> None:
    consolidated = chunker.load_consolidated(args.consolidated)
    table = chunker.choose_table(consolidated.get("data", {}), preferred=args.table)
    rows = chunker.make_rows(consolidated, table)

    # Build chunks once, then create two iterables from materialized list
    chunk_list = list(_iter_chunks(rows, table=table, rows_per_chunk=args.rows_per_chunk))

    # Compute ground truth
    gt = _compute_ground_truth(chunk_list, sum_field=args.sum_field)

    # Run questions via model
    options = {"temperature": args.temperature}
    results = run_questions_over_chunks(
        model=args.model,
        chunks=chunk_list,
        sum_field=args.sum_field,
        endpoint=args.endpoint,
        options=options,
        format_name=args.format,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results_path = out_dir / "results.jsonl"
    gt_path = out_dir / "ground_truth.json"
    report_path = out_dir / "report.json"

    save_results(results, results_path)
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(gt, f, ensure_ascii=False, indent=2)

    report = score_results(str(results_path), ground_truth=gt)
    save_report(report, report_path)
    print(f"Saved: {report_path}")
    print(f"Accuracy: {report['accuracy']:.3f} | Avg latency: {report['avg_latency_s']:.3f}s")


def cmd_run(args: argparse.Namespace) -> None:
    consolidated = chunker.load_consolidated(args.consolidated)
    table = chunker.choose_table(consolidated.get("data", {}), preferred=args.table)
    rows = chunker.make_rows(consolidated, table)
    chunk_list = list(_iter_chunks(rows, table=table, rows_per_chunk=args.rows_per_chunk))

    options = {"temperature": args.temperature}
    results = run_questions_over_chunks(
        model=args.model,
        chunks=chunk_list,
        sum_field=args.sum_field,
        endpoint=args.endpoint,
        options=options,
        format_name=args.format,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_results(results, out_path)
    print(f"OK: results saved to {out_path}")


def cmd_score(args: argparse.Namespace) -> None:
    with open(args.ground_truth, "r", encoding="utf-8") as f:
        gt = json.load(f)
    report = score_results(args.results, gt)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_report(report, out_path)
    print(f"OK: report saved to {out_path}")
    print(f"Accuracy: {report['accuracy']:.3f} | Avg latency: {report['avg_latency_s']:.3f}s")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("llm-eval")
    sub = p.add_subparsers(dest="cmd", required=True)

    # eval (end-to-end)
    pe = sub.add_parser("eval", help="Run model over chunks and score outputs")
    pe.add_argument("--consolidated", default="consolidated.json")
    pe.add_argument("--table", default=None)
    pe.add_argument("--rows-per-chunk", type=int, default=200)
    pe.add_argument("--sum-field", default=None, help="Optional flattened field name to sum")
    pe.add_argument("--model", required=True, help="Ollama model (e.g., llama3.1:8b)")
    pe.add_argument("--format", default="jsonl", choices=list_formats(), help="Formato dos dados enviados ao modelo")
    pe.add_argument("--endpoint", default="http://localhost:11434")
    pe.add_argument("--temperature", type=float, default=0.0)
    pe.add_argument("--out-dir", default="results/latest")
    pe.set_defaults(func=cmd_eval)

    # list-models
    pm = sub.add_parser("list-models", help="List local Ollama models and rank them")
    pm.add_argument("--endpoint", default="http://localhost:11434")
    pm.add_argument("--out", default="models_local.json")
    pm.set_defaults(func=cmd_list_models)

    # prepare-run: create plan file
    pp = sub.add_parser("prepare-run", help="Create batch evaluation plan file")
    pp.add_argument("--models-file", required=True, help="JSON file from list-models or manual list")
    pp.add_argument("--select", required=True, help="Comma-separated model names to include")
    pp.add_argument("--formats", default="jsonl,token_object", help="Comma-separated formats")
    pp.add_argument("--rows-per-chunk", type=int, default=40)
    pp.add_argument("--sum-field", default="vl")
    pp.add_argument("--endpoint", default="http://localhost:11434")
    pp.add_argument("--out", default="eval_plan.json")
    pp.set_defaults(func=cmd_prepare_run)

    # run-batch using plan
    pb = sub.add_parser("run-batch", help="Execute batch evaluation per plan file")
    pb.add_argument("--plan", required=True)
    pb.add_argument("--endpoint", default=None, help="Override endpoint in plan")
    pb.add_argument("--model-options", default=None, help="key=value comma separated (e.g. temperature=0)")
    pb.add_argument("--sample-preview", action="store_true", help="Mostrar amostra do prompt/dados uma única vez por formato/pergunta")
    pb.add_argument("--sample-chars", type=int, default=600, help="Máximo de caracteres exibidos na amostra")
    pb.set_defaults(func=cmd_run_batch)

    # consolidate results
    pc = sub.add_parser("consolidate", help="Consolidate results from batch run")
    pc.add_argument("--plan", required=True)
    pc.add_argument("--results-root", default="results")
    pc.add_argument("--out-json", default="summary/summary.json")
    pc.add_argument("--out-md", default="summary/summary.md")
    pc.set_defaults(func=cmd_consolidate)

    # auto-plan: list + auto-select + write plan
    ap = sub.add_parser("auto-plan", help="List, auto-select representative models and create plan")
    ap.add_argument("--endpoint", default="http://localhost:11434")
    ap.add_argument("--desired", type=int, default=5)
    ap.add_argument("--formats", default="jsonl,token_object")
    ap.add_argument("--rows-per-chunk", type=int, default=40)
    ap.add_argument("--sum-field", default="vl")
    ap.add_argument("--out", default="eval_plan.json")
    ap.add_argument("--require-family-diversity", action="store_true", help="Try to avoid duplicate families")
    ap.set_defaults(func=cmd_auto_plan)

    # run-only
    pr = sub.add_parser("run", help="Run model over chunks and save results JSONL")
    pr.add_argument("--consolidated", default="consolidated.json")
    pr.add_argument("--table", default=None)
    pr.add_argument("--rows-per-chunk", type=int, default=200)
    pr.add_argument("--sum-field", default=None)
    pr.add_argument("--model", required=True)
    pr.add_argument("--format", default="jsonl", choices=list_formats())
    pr.add_argument("--endpoint", default="http://localhost:11434")
    pr.add_argument("--temperature", type=float, default=0.0)
    pr.add_argument("--out", default="results/run.jsonl")
    pr.set_defaults(func=cmd_run)

    # score-only
    ps = sub.add_parser("score", help="Score results JSONL against a ground-truth JSON")
    ps.add_argument("--results", required=True)
    ps.add_argument("--ground-truth", required=True)
    ps.add_argument("--out", default="results/report.json")
    ps.set_defaults(func=cmd_score)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


def cmd_list_models(args: argparse.Namespace) -> None:
    models = fetch_local_models(endpoint=args.endpoint)
    ranked = rank_models(models)
    save_models(ranked, args.out)
    print(f"OK: {len(ranked)} modelos salvos em {args.out}")
    for m in ranked[:10]:
        print(f"#{m['rank']} {m['name']} params={m.get('parameter_size')} size={m.get('size_bytes')} family={m.get('family')}")


def cmd_prepare_run(args: argparse.Namespace) -> None:
    with open(args.models_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    available = {m['name']: m for m in data.get('models', [])}
    selected = [s.strip() for s in args.select.split(',') if s.strip()]
    missing = [s for s in selected if s not in available]
    if missing:
        print(f"Aviso: modelos não encontrados: {missing}")
    plan = {
        'endpoint': args.endpoint,
        'models': selected,
        'formats': [fmt.strip() for fmt in args.formats.split(',') if fmt.strip()],
        'rows_per_chunk': args.rows_per_chunk,
        'sum_field': args.sum_field,
    }
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"OK: plano salvo em {args.out}")


def cmd_run_batch(args: argparse.Namespace) -> None:
    with open(args.plan, 'r', encoding='utf-8') as f:
        plan = json.load(f)
    endpoint = args.endpoint or plan.get('endpoint') or 'http://localhost:11434'
    models = plan['models']
    formats = plan['formats']
    rows_per_chunk = plan['rows_per_chunk']
    sum_field = plan.get('sum_field')
    options = None
    if args.model_options:
        opts = {}
        for kv in args.model_options.split(','):
            if '=' in kv:
                k,v = kv.split('=',1)
                try:
                    v_cast = float(v)
                except ValueError:
                    v_cast = v
                opts[k]=v_cast
        options = opts
    consolidated_path = plan.get('consolidated', 'consolidated.json')
    consolidated = chunker.load_consolidated(consolidated_path)
    table = chunker.choose_table(consolidated.get('data', {}), preferred=None)
    rows = chunker.make_rows(consolidated, table)
    chunk_list = list(_iter_chunks(rows, table=table, rows_per_chunk=rows_per_chunk))
    gt = _compute_ground_truth(chunk_list, sum_field=sum_field)

    preview_enabled = getattr(args, 'sample_preview', False)
    preview_chars = getattr(args, 'sample_chars', 600)
    preview_anchor: Dict[Tuple[str, str], str] = {}
    preview_notified: set[Tuple[str, str, str]] = set()

    def build_preview_callback(model_name: str):
        if not preview_enabled:
            return None

        def _cb(info: Dict[str, Any]) -> None:
            fmt = info['format']
            question = info['question']
            combo = (fmt, question)
            label = f"fmt={fmt} | pergunta={question} | chunk={info['chunk_id']} | modelo={model_name}"
            if combo not in preview_anchor:
                preview_anchor[combo] = model_name
                _print_prompt_preview(label, info['prompt'], max_chars=preview_chars)
            else:
                anchor = preview_anchor[combo]
                if model_name != anchor:
                    key = (model_name, fmt, question)
                    if key not in preview_notified:
                        print(f"[preview] {model_name} reutiliza prompt já exibido para {anchor} (fmt={fmt}, pergunta={question})")
                        preview_notified.add(key)

        return _cb

    for model in models:
        for fmt in formats:
            out_dir = Path('results') / model.replace(':','_') / fmt
            out_dir.mkdir(parents=True, exist_ok=True)
            results = run_questions_over_chunks(
                model=model,
                chunks=chunk_list,
                sum_field=sum_field,
                endpoint=endpoint,
                options=options,
                format_name=fmt,
                preview_callback=build_preview_callback(model),
            )
            results_path = out_dir / 'results.jsonl'
            gt_path = out_dir / 'ground_truth.json'
            report_path = out_dir / 'report.json'
            save_results(results, results_path)
            with open(gt_path, 'w', encoding='utf-8') as f:
                json.dump(gt, f, ensure_ascii=False, indent=2)
            report = score_results(str(results_path), ground_truth=gt)
            save_report(report, report_path)
            print(f"OK: {model} fmt={fmt} acc={report['accuracy']:.2f} latency={report['avg_latency_s']:.2f}")


def cmd_consolidate(args: argparse.Namespace) -> None:
    data = consolidate(args.plan, args.results_root)
    save_consolidated(data, args.out_json, args.out_md)
    print(f"OK: consolidação salva em {args.out_json} e {args.out_md}")


def cmd_auto_plan(args: argparse.Namespace) -> None:
    models = fetch_local_models(endpoint=args.endpoint)
    ranked = rank_models(models)
    names, subset = auto_select_models(ranked, desired=args.desired, require_family_diversity=args.require_family_diversity)
    plan = {
        'endpoint': args.endpoint,
        'models': names,
        'formats': [f.strip() for f in args.formats.split(',') if f.strip()],
        'rows_per_chunk': args.rows_per_chunk,
        'sum_field': args.sum_field,
        'selection': subset,
    }
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"OK: auto-plan criado em {args.out} com modelos: {', '.join(names)}")


def _print_prompt_preview(label: str, prompt: str, max_chars: int = 600) -> None:
    clean = prompt.replace('\r', '')
    snippet = clean
    if len(clean) > max_chars:
        snippet = clean[:max_chars] + "\n... [conteúdo truncado, total de %d caracteres]" % len(clean)
    print(f"\n--- PREVIEW {label} ---")
    print(snippet)
    print("--- FIM PREVIEW ---\n")


if __name__ == "__main__":
    main()
