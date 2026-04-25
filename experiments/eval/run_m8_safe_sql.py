"""M8 — Safe-SQL style hints: isolated flag ablation.

Each flag adds a STYLE hint (not a concrete example) to the baseline prompt.
Baseline = M2 FEWSHOT_BLOCK only (basic JOIN example, no HAVING addendum,
no L3 examples). Style hints are pure directives about SQL patterns to use
or avoid.

Variants tested:
  baseline               no style hint
  safe_having            avoid HAVING with outer COUNT; decompose via subquery
  safe_subquery_col      explicit column naming in inner subquery (no bare 'id')
  safe_name_join         JOIN to dim table to return names, never FK IDs
  safe_explicit_fk       FK lives in fact table, descriptive col lives in dim

Questions covered (3 known failure points):
  q_having              L2, F-Q19 target (HAVING scope confusion)
  q_top_e1_best_e2      L3, F-Q20 target (column confusion in nested subquery)
  q_e2_most_e1          L3, F-Q20 target (ID vs name output)

Design: 3 models × 3 domains × 3 questions × 5 variants × 3 seeds = 405 combos.
Each variant tested on ALL questions to detect off-target side effects.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_sources import load_dataset
from llm_eval.ollama_client import OllamaClient
from run_m1_codegen import LLM_OPTIONS, PROMPT_TEMPLATE, build_sqlite_from_tables, extract_sql, score_sql
from run_m2_codegen import FEWSHOT_BLOCK, build_payload_stats
from run_m6_filter_questions import DOMAIN_CONFIGS, compute_gt_m6, build_questions_m6
from run_m7_complex_queries import compute_gt_m7, build_questions_m7


RESULTS_DIR = ROOT / "experiments" / "results" / "m8_safe_sql"


# ---------------------------------------------------------------------------
# Style hint blocks (4 independent flags)
# ---------------------------------------------------------------------------

STYLE_HAVING = """
## Estilo SQL — filtros em agregacao
Ao filtrar por um valor agregado (COUNT, SUM, etc.) no resultado final:
- NUNCA aplique HAVING diretamente num SELECT cujo resultado e uma contagem externa.
- Decomponha em subquery: primeiro agregue e filtre os grupos, depois conte os grupos.
- Padrao correto: SELECT COUNT(*) FROM (SELECT chave FROM tabela GROUP BY chave HAVING agg_cond)
"""

STYLE_SUBQUERY_COL = """
## Estilo SQL — colunas em subqueries
Em subqueries aninhadas no WHERE, sempre referencie a coluna pelo seu nome
completo (ex: id_paciente, id_cliente), NUNCA apenas 'id'. O 'id' em cada
tabela refere-se ao id dela propria, nao a FK. A subquery interna deve
selecionar a mesma coluna que sera comparada no WHERE externo.
"""

STYLE_NAME_JOIN = """
## Estilo SQL — retornar nomes, nao IDs
Quando a pergunta pede "qual entidade", "qual produto", "qual cliente", etc.,
o resultado final DEVE ser o nome/label da entidade, nao o FK numerico.
Sempre faca JOIN com a tabela de dimensao e selecione a coluna de nome
(ex: d.nome, p.nome, c.titular), NUNCA o FK puro (id_categoria, id_produto).
"""

STYLE_EXPLICIT_FK = """
## Estilo SQL — localizacao de colunas FK vs descritivas
FKs (id_X) vivem na tabela FATO. Colunas descritivas (nome, titular, label)
vivem na tabela DIMENSAO. Nao assuma que a tabela fato tem coluna descritiva.
Exemplo: em 'transacoes' (fato) existe id_conta; o 'titular' vive em 'contas'
(dim). Para filtrar por titular, faca JOIN com contas.
"""


STYLE_BLOCKS = {
    "baseline": "",
    "safe_having": STYLE_HAVING,
    "safe_subquery_col": STYLE_SUBQUERY_COL,
    "safe_name_join": STYLE_NAME_JOIN,
    "safe_explicit_fk": STYLE_EXPLICIT_FK,
}


def build_payload(tables: dict, meta: dict, variant: str) -> str:
    """Baseline M2 fewshot + optional style hint."""
    base = build_payload_stats(tables, meta) + "\n" + FEWSHOT_BLOCK
    style = STYLE_BLOCKS[variant]
    return base + style


# ---------------------------------------------------------------------------
# Question bundle (3 known failure points)
# ---------------------------------------------------------------------------

def build_m8_questions(cfg: dict, tables: dict) -> tuple[dict, dict]:
    """Return combined {q_name: q_dict} and combined GT dict."""
    gt6 = compute_gt_m6(tables, cfg)
    gt7 = compute_gt_m7(tables, cfg)
    q6 = build_questions_m6(cfg, gt6)
    q7 = build_questions_m7(cfg, gt7)
    questions = {
        "q_having":          q6["q_having"],
        "q_top_e1_best_e2":  q7["q_top_e1_best_e2"],
        "q_e2_most_e1":      q7["q_e2_most_e1"],
    }
    gt = {**gt6, **gt7}
    return questions, gt


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------

def _load_completed(manifest_path: Path) -> set[str]:
    if not manifest_path.exists():
        return set()
    out: set[str] = set()
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("reason") != "exception":
            out.add(r["key"])
    return out


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_m8(
    models: list[str], n_orders: int, domains: list[str],
    seeds: list[int], variants: list[str], endpoint: str,
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"
    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    per_state: dict[tuple[str, int], dict] = {}
    for domain in domains:
        cfg = DOMAIN_CONFIGS[domain]
        for seed in seeds:
            tables, meta = load_dataset(cfg["source"], n_orders=n_orders, seed=seed)
            questions, gt = build_m8_questions(cfg, tables)
            conn = build_sqlite_from_tables(tables)
            per_state[(domain, seed)] = {
                "gt": gt, "conn": conn, "questions": questions,
                "tables": tables, "meta": meta, "cfg": cfg,
            }

    combos = []
    for domain in domains:
        for seed in seeds:
            state = per_state[(domain, seed)]
            for model in models:
                for variant in variants:
                    for q_name, q in state["questions"].items():
                        key = f"m8|{model}|{domain}|{variant}|n{n_orders}|s{seed}|{q_name}"
                        if key not in completed:
                            combos.append({
                                "key": key, "model": model, "domain": domain,
                                "seed": seed, "variant": variant,
                                "q_name": q_name, "q": q,
                            })

    total = len(domains) * len(models) * len(seeds) * len(variants) * 3
    print(f"[M8] {len(domains)}d x {len(models)}m x {len(variants)}v x 3q x {len(seeds)}s = {total} combos")
    print(f"     {len(combos)} to run, {len(completed)} cached\n")

    t_start = time.time()
    warmed: set[str] = set()
    payload_cache: dict[tuple, str] = {}

    for i, c in enumerate(combos, 1):
        model = c["model"]
        state = per_state[(c["domain"], c["seed"])]
        variant = c["variant"]

        pkey = (c["domain"], c["seed"], variant)
        if pkey not in payload_cache:
            payload_cache[pkey] = build_payload(state["tables"], state["meta"], variant)
        payload = payload_cache[pkey]

        if model not in warmed:
            print(f"  warming {model} ...")
            try:
                client.generate(model, "ok",
                                options={**LLM_OPTIONS, "num_predict": 2, "think": False},
                                timeout=300)
            except Exception as e:
                print(f"  warm failed: {e}", file=sys.stderr)
            warmed.add(model)

        prompt = PROMPT_TEMPLATE.format(payload=payload, question=c["q"]["text"])
        elapsed = time.time() - t_start
        print(f"  [{i}/{len(combos)} el={elapsed:.0f}s] {c['key']}", end=" ", flush=True)

        call_options = {**LLM_OPTIONS, "think": False}
        response, ok, reason, executed, sql, total_ms = "", False, "exception", "", "", 0

        for attempt in (1, 2):
            try:
                result = client.generate(model, prompt, options=call_options)
                response = result["text"]
                total_ms = result.get("total_duration_ns", 0) // 1_000_000
                sql = extract_sql(response)
                ok, reason, executed = score_sql(c["q"], sql, state["conn"], state["gt"])
                print(f"{'OK' if ok else 'NO'} ({reason})")
                break
            except Exception as e:
                es = str(e)
                transient = any(x in es for x in ("RemoteDisconnected", "ConnectionError",
                                                   "ConnectionAborted", "ReadTimeout"))
                if transient and attempt == 1:
                    print(f"TRANSIENT; retry 15s...", flush=True)
                    time.sleep(15)
                    continue
                print(f"ERROR: {e}")
                response = f"ERROR:{e}"
                break

        record = {
            "key": c["key"], "phase": "m8", "model": model,
            "domain": c["domain"], "variant": variant,
            "question": c["q_name"], "question_key": c["q"]["key"],
            "question_type": c["q"]["type"],
            "seed": c["seed"], "n_orders": n_orders,
            "response": response, "sql": sql, "executed_result": executed,
            "ok": ok, "reason": reason,
            "expected": str(state["gt"][c["q"]["key"]]),
            "prompt_chars": len(prompt), "total_ms": total_ms,
        }
        with open(manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    for state in per_state.values():
        state["conn"].close()

    print_summary(manifest_path)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M8] No records.")
        return
    seen: set[str] = set()
    records = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r["key"] not in seen:
            seen.add(r["key"])
            records.append(r)

    total = len(records)
    ok_count = sum(r["ok"] for r in records)
    print(f"\n=== M8 Summary ({total} records) ===")
    print(f"  Overall: {ok_count}/{total} = {ok_count/total*100:.1f}%\n")

    # Accuracy per (variant × question)
    by_vq = defaultdict(list)
    for r in records:
        by_vq[(r["variant"], r["question"])].append(r["ok"])

    variants = ["baseline", "safe_having", "safe_subquery_col", "safe_name_join", "safe_explicit_fk"]
    questions = ["q_having", "q_top_e1_best_e2", "q_e2_most_e1"]

    print("  Variant × Question (accuracy %):\n")
    header = f"  {'Variant':<22}"
    for q in questions:
        header += f"  {q:<20}"
    header += "  Agg"
    print(header)
    print(f"  {'-'*22}  " + "  ".join("-" * 20 for _ in questions) + "  ---")
    for v in variants:
        row = f"  {v:<22}"
        agg_oks = []
        for q in questions:
            oks = by_vq.get((v, q), [])
            if oks:
                acc = sum(oks) / len(oks) * 100
                row += f"  {sum(oks):>2}/{len(oks):<2} ({acc:>5.1f}%)   "
                agg_oks.extend(oks)
            else:
                row += f"  {'—':<20}  "
        if agg_oks:
            row += f"  {sum(agg_oks)}/{len(agg_oks)} ({sum(agg_oks)/len(agg_oks)*100:.0f}%)"
        print(row)

    # Delta baseline vs each flag
    print("\n  Delta vs baseline (pp) per question:\n")
    base_acc = {q: 0.0 for q in questions}
    for q in questions:
        oks = by_vq.get(("baseline", q), [])
        base_acc[q] = sum(oks) / len(oks) * 100 if oks else 0.0

    print(f"  {'Flag':<22}" + "  ".join(f"{q:<20}" for q in questions))
    print(f"  {'-'*22}" + "  " + "  ".join("-" * 20 for _ in questions))
    for v in variants:
        if v == "baseline":
            continue
        row = f"  {v:<22}"
        for q in questions:
            oks = by_vq.get((v, q), [])
            if oks:
                acc = sum(oks) / len(oks) * 100
                delta = acc - base_acc[q]
                sign = "+" if delta >= 0 else ""
                row += f"  {sign}{delta:>+5.1f}pp ({acc:.0f}%)      "
            else:
                row += f"  {'—':<20}"
        print(row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="M8 - Safe-SQL style hint ablation")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"])
    parser.add_argument("--domains", nargs="+", default=["retail", "medical", "financial"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--variants", nargs="+", default=list(STYLE_BLOCKS.keys()))
    parser.add_argument("--n-orders", type=int, default=100)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    if args.dry_run:
        for variant in args.variants:
            cfg = DOMAIN_CONFIGS[args.domains[0]]
            tables, meta = load_dataset(cfg["source"], n_orders=args.n_orders, seed=42)
            payload = build_payload(tables, meta, variant)
            print(f"\n=== Variant: {variant} ===")
            print(f"Payload length: {len(payload)} chars")
            # Show only the style hint portion
            style = STYLE_BLOCKS[variant]
            if style:
                print(f"Style block:\n{style}")
            else:
                print("(no style hint)")
        return

    run_m8(args.models, args.n_orders, args.domains,
           args.seeds, args.variants, args.endpoint)


if __name__ == "__main__":
    main()
