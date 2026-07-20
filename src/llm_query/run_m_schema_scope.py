"""M-schema-scope — eixo horizontal: schema escopo afeta accuracy SQL gen?

Hypothesis (do ticket M-schema-scope.md):
  H_scope-1: schema reduzido pode CAUSAR falhas (informação faltante)
  H_scope-2: schema excessivo pode CAUSAR ruído (mais tabelas para confundir)
  H_scope-3: efeito é moderado pela naturalidade da pergunta

Design: TPC-H sf001 com 4 níveis de schema visível no payload (mas
o SQLite mantém todas 3 tabelas necessárias para o GT — quando schema
é reduzido, o modelo VÊ menos mas a database TEM tudo).

Schema levels (subset em payload, db sempre completa):
  - minimal: só fact (partsupp) → q_top_product e q_lookup precisam de JOIN
              que o modelo não consegue ver
  - core:    fact + dim2 (partsupp + part) → q_lookup ainda falta
  - chain:   fact + dim1 + dim2 (partsupp + supplier + part) → BASELINE
              (igual M9-canonical e F-Q33)
  - full:    8 tabelas TPC-H → schema excessivo (testa "noise")

Compara accuracy entre níveis para registrar F-Q37.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts"))

from llm_eval.ollama_client import OllamaClient
from llm_eval.question_naturalness import (
    NaturalnessLevel, get_questions as get_natural_questions, iter_levels,
)
from run_m1_codegen import (
    LLM_OPTIONS, PROMPT_TEMPLATE, build_sqlite_from_tables,
    extract_sql, score_sql, _coerce_value, _detect_column_type,
)
from run_m9_canonical import (
    CANONICAL_CONFIGS, compute_gt_m9, build_payload_canonical,
)
from data_sources import load_dataset


RESULTS_DIR = ROOT / "experiments" / "results" / "m_schema_scope"

# Schema levels for TPC-H — varies what the LLM sees in payload only.
# The SQLite db is always loaded with all 3 chain tables so GT is computable.
SCHEMA_LEVELS_VISIBLE = {
    "minimal": ["partsupp"],                         # fact only
    "core":    ["partsupp", "part"],                  # fact + dim2
    "chain":   ["partsupp", "part", "supplier"],      # fact + both dims (M9 baseline)
    "full":    ["partsupp", "part", "supplier",
                "orders", "customer", "lineitem",
                "nation", "region"],                  # all 8 TPC-H tables
}


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


def run(
    models: list[str], volume: int, seeds: list[int],
    schema_levels: list[str], endpoint: str,
    naturalness: tuple[NaturalnessLevel, ...] = (NaturalnessLevel.N0,),
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"
    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    cfg = CANONICAL_CONFIGS["tpch-sf001"]

    # Pre-compute GT over the chain (3 tables) — same as M9-canonical.
    # Per seed: load full chain, build SQLite, compute GT, then build
    # payload variants by filtering tables visible.
    per_seed: dict[int, dict] = {}
    for seed in seeds:
        # Always load 'chain' tables for GT
        tables_chain, meta = load_dataset(
            "canonical:tpch-sf001",
            volume=volume, seed=seed,
            schema=["partsupp", "part", "supplier"],
            fact_table="partsupp",
        )
        gt = compute_gt_m9(tables_chain, cfg)
        # SQLite always has all 3 tables (so generated SQL can JOIN even when
        # the model "shouldn't" know about them — measures over-reach)
        conn = build_sqlite_from_tables(tables_chain)

        # For 'full', also load extra tables (best-effort; if not available
        # in shaper for FK-preserving sample, only chain is shown anyway)
        try:
            tables_full, meta_full = load_dataset(
                "canonical:tpch-sf001",
                volume=volume, seed=seed,
                schema=SCHEMA_LEVELS_VISIBLE["full"],
                fact_table="partsupp",
            )
        except Exception:
            tables_full = tables_chain
            meta_full = meta

        per_seed[seed] = {
            "gt": gt, "conn": conn,
            "tables_chain": tables_chain, "meta_chain": meta,
            "tables_full": tables_full, "meta_full": meta_full,
        }

    # Build payloads per (seed, schema_level)
    per_seed_level: dict[tuple[int, str], dict] = {}
    for seed in seeds:
        st = per_seed[seed]
        for sl in schema_levels:
            if sl == "full":
                src_tables, src_meta = st["tables_full"], st["meta_full"]
            else:
                src_tables, src_meta = st["tables_chain"], st["meta_chain"]
            visible = set(SCHEMA_LEVELS_VISIBLE[sl])
            filtered = {n: rs for n, rs in src_tables.items() if n in visible}
            payload = build_payload_canonical(filtered, src_meta)
            per_seed_level[(seed, sl)] = {"payload": payload, "n_tables": len(filtered)}

    combos = []
    for model in models:
        for seed in seeds:
            for sl in schema_levels:
                for nl in naturalness:
                    questions = get_natural_questions("tpch", nl)
                    for q_name, q in questions.items():
                        key = f"mscope|{model}|tpch|vol{volume}|s{seed}|{sl}|{nl.value}|{q_name}"
                        if key in completed:
                            continue
                        combos.append({
                            "key": key, "model": model, "seed": seed,
                            "schema_level": sl, "naturalness": nl,
                            "q_name": q_name, "q": q,
                        })

    total = len(seeds) * len(models) * len(schema_levels) * len(naturalness) * 7
    sl_str = ",".join(schema_levels)
    nl_str = ",".join(nl.value for nl in naturalness)
    print(f"[M-Schema-Scope] {len(models)}m x 7q x {len(seeds)}s x {len(schema_levels)}sl ({sl_str}) x {len(naturalness)}nl ({nl_str}) = {total} combos")
    print(f"                 {len(combos)} to run, {len(completed)} cached\n")

    # Preview
    seed0 = seeds[0]
    print(f"  GT preview seed={seed0}: {per_seed[seed0]['gt']}")
    for sl in schema_levels:
        st = per_seed_level[(seed0, sl)]
        print(f"    {sl:<8}: {st['n_tables']} tables, payload {len(st['payload']):,} chars")
    print()

    t_start = time.time()
    warmed: set[str] = set()

    for i, c in enumerate(combos, 1):
        model = c["model"]
        st_seed = per_seed[c["seed"]]
        st_lvl = per_seed_level[(c["seed"], c["schema_level"])]

        if model not in warmed:
            print(f"  warming {model} ...")
            try:
                client.generate(model, "ok",
                                options={**LLM_OPTIONS, "num_predict": 2, "think": False},
                                timeout=300)
            except Exception as e:
                print(f"  warm failed: {e}", file=sys.stderr)
            warmed.add(model)

        prompt = PROMPT_TEMPLATE.format(payload=st_lvl["payload"], question=c["q"]["text"])
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
                ok, reason, executed = score_sql(c["q"], sql, st_seed["conn"], st_seed["gt"])
                print(f"{'OK' if ok else 'NO'} ({reason}) -> {str(executed)[:35]}")
                break
            except Exception as e:
                es = str(e)
                transient = any(x in es for x in ("RemoteDisconnected", "ConnectionError",
                                                   "ConnectionAborted", "ReadTimeout"))
                if transient and attempt == 1:
                    print("TRANSIENT; retry 15s...", flush=True)
                    time.sleep(15)
                    continue
                print(f"ERROR: {e}")
                response = f"ERROR:{e}"
                break

        record = {
            "key": c["key"], "phase": "m_schema_scope", "model": model,
            "dataset": "tpch-sf001", "variant": "sql_stats_fs",
            "schema_level": c["schema_level"],
            "n_tables_visible": st_lvl["n_tables"],
            "naturalness_level": c["naturalness"].value,
            "question": c["q_name"], "question_key": c["q"]["key"],
            "question_type": c["q"]["type"],
            "question_text": c["q"]["text"],
            "seed": c["seed"], "volume": volume,
            "response": response, "sql": sql, "executed_result": executed,
            "ok": ok, "reason": reason,
            "expected": str(st_seed["gt"][c["q"]["key"]]),
            "prompt_chars": len(prompt), "total_ms": total_ms,
        }
        with open(manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    for st in per_seed.values():
        st["conn"].close()

    print_summary(manifest_path)


def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M-Schema-Scope] No records.")
        return
    by_key: dict[str, dict] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        by_key[r["key"]] = r
    records = list(by_key.values())
    if not records:
        return

    total = len(records)
    ok = sum(r["ok"] for r in records)
    print(f"\n=== M-Schema-Scope Summary ({total} records) ===")
    print(f"  Overall: {ok}/{total} = {ok/total*100:.1f}%\n")

    levels = sorted({r.get("schema_level", "?") for r in records},
                    key=lambda s: ["minimal", "core", "chain", "full"].index(s)
                    if s in ["minimal", "core", "chain", "full"] else 999)
    nls = sorted({r.get("naturalness_level", "N0") for r in records})
    multi_nl = len(nls) > 1

    by_ms = defaultdict(list)
    by_sl_q = defaultdict(list)
    by_sl_nl = defaultdict(list)
    for r in records:
        sl = r.get("schema_level", "?")
        nl = r.get("naturalness_level", "N0")
        by_ms[(r["model"], sl)].append(r["ok"])
        by_sl_q[(sl, r["question"])].append(r["ok"])
        by_sl_nl[(sl, nl)].append(r["ok"])

    questions = ["q_count", "q_sum", "q_avg", "q_distinct",
                 "q_top_product", "q_lookup", "q_lookup_value"]
    models = sorted(set(r["model"] for r in records))

    print(f"  Per (model x schema_level):")
    print(f"  {'Model':<22}" + "  ".join(f"{l:<14}" for l in levels))
    for m in models:
        row = f"  {m:<22}"
        for l in levels:
            oks = by_ms.get((m, l), [])
            if oks:
                row += f"  {sum(oks)}/{len(oks)} ({sum(oks)/len(oks)*100:.0f}%)    "
            else:
                row += f"  {'-':<14}"
        print(row)

    print(f"\n  Per (schema_level x question):")
    print(f"  {'Question':<22}" + "  ".join(f"{l:<14}" for l in levels))
    for q in questions:
        row = f"  {q:<22}"
        for l in levels:
            oks = by_sl_q.get((l, q), [])
            if oks:
                row += f"  {sum(oks)}/{len(oks)} ({sum(oks)/len(oks)*100:.0f}%)    "
            else:
                row += f"  {'-':<14}"
        print(row)

    if multi_nl:
        print(f"\n  Per (schema_level x naturalness):")
        print(f"  {'Level':<10}" + "  ".join(f"{nl:<14}" for nl in nls))
        for l in levels:
            row = f"  {l:<10}"
            for nl in nls:
                oks = by_sl_nl.get((l, nl), [])
                if oks:
                    row += f"  {sum(oks)}/{len(oks)} ({sum(oks)/len(oks)*100:.0f}%)    "
                else:
                    row += f"  {'-':<14}"
            print(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="M-Schema-Scope — horizontal axis (TPC-H schema breadth)")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--volume", type=int, default=100)
    parser.add_argument("--schema-levels", nargs="+",
                        default=["minimal", "core", "chain", "full"],
                        choices=list(SCHEMA_LEVELS_VISIBLE.keys()))
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--naturalness", default="N0")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    levels = tuple(iter_levels(args.naturalness))
    run(args.models, args.volume, args.seeds, args.schema_levels,
        args.endpoint, naturalness=levels)


if __name__ == "__main__":
    main()
