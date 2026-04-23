"""M1 — Code Generation Probe: TCF as schema carrier for SQL generation.

Hypothesis H-TCF2: TCF header + column statistics, sent to a code-generating
LLM, produces SQL that when executed against SQLite gives correct aggregation
answers — unlike direct-reading TCF which fails universally on sum/avg (Phase 6).

Payload variants:
  sql_full    : full TCF L3 data + "generate SQL" (cost-heavy baseline)
  sql_schema  : just column names+types per table (minimal)
  sql_stats   : schema + column statistics + FK hints (the hypothesis)

Backend: in-memory SQLite built from the same synthetic fixtures as Phase 6.
The generated SQL is executed deterministically, so arithmetic is exact.
"""
from __future__ import annotations
import argparse
import json
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tcf import encode as tcf_encode, EncodeConfig
from tests.fixtures import _write_fixture
from tests.fixtures.synthetic_v2 import retail_sales

from llm_eval.ollama_client import OllamaClient


RESULTS_DIR = ROOT / "experiments" / "results" / "m1_codegen"
LLM_OPTIONS = {
    "temperature": 0, "seed": 42, "keep_alive": "30m",
    "num_ctx": 8192, "num_predict": 2048,
}

# Canonical questions (mirroring frontier_search so results are comparable)
QUESTIONS: dict[str, dict] = {
    "q_count": {
        "text": "Quantas linhas existem na tabela vendas?",
        "key": "count", "type": "count",
    },
    "q_top_product": {
        "text": "Qual produto aparece mais vezes em vendas? Responda com o nome do produto.",
        "key": "top_product", "type": "string",
    },
    "q_distinct": {
        "text": "Quantos clientes distintos aparecem na tabela vendas?",
        "key": "distinct_customers", "type": "count",
    },
    "q_sum": {
        "text": "Qual e a soma de todos os valores da coluna total em vendas?",
        "key": "sum_total", "type": "numeric",
    },
    "q_lookup": {
        "text": "Qual cliente realizou a venda individual de maior valor? Responda com o nome do cliente.",
        "key": "max_buyer", "type": "string",
    },
    "q_lookup_value": {
        "text": "Qual e o maior valor individual da coluna total em vendas?",
        "key": "max_total_row", "type": "numeric",
    },
    "q_avg": {
        "text": "Qual e a media da coluna total em vendas?",
        "key": "avg_total", "type": "numeric",
    },
}


# ---------------------------------------------------------------------------
# Ground truth (same semantics as frontier_search._compute_gt)
# ---------------------------------------------------------------------------

def _compute_gt(tables: dict) -> dict:
    clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
    produtos = {p["id"]: p["nome"] for p in tables["produtos"]}
    vendas = tables["vendas"]
    totals = [float(v["total"]) for v in vendas if v["total"]]
    n = len(vendas)
    prod_counter = Counter(v["id_produto"] for v in vendas)
    cli_counter = Counter(v["id_cliente"] for v in vendas)
    top_pid = prod_counter.most_common(1)[0][0]
    top_cid = cli_counter.most_common(1)[0][0]
    max_venda = max(vendas, key=lambda v: float(v["total"]) if v["total"] else 0)
    return {
        "count": n,
        "sum_total": round(sum(totals), 2),
        "avg_total": round(sum(totals) / n, 2) if n else 0,
        "top_product": produtos.get(top_pid, top_pid),
        "top_customer": clientes.get(top_cid, top_cid),
        "distinct_customers": len(set(v["id_cliente"] for v in vendas)),
        "max_buyer": clientes.get(max_venda["id_cliente"], max_venda["id_cliente"]),
        "max_total_row": float(max_venda["total"]) if max_venda["total"] else 0.0,
    }


# ---------------------------------------------------------------------------
# SQLite backend
# ---------------------------------------------------------------------------

_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")
_BOOL_SET = {"true", "false", "True", "False", "TRUE", "FALSE"}


def _coerce_value(v):
    """Coerce string values to int/float/bool when they look numeric/boolean."""
    if v is None or isinstance(v, (int, float, bool)):
        return v
    s = str(v)
    if s in _BOOL_SET:
        return s.lower() == "true"
    if _INT_RE.match(s):
        try: return int(s)
        except ValueError: pass
    if _FLOAT_RE.match(s):
        try: return float(s)
        except ValueError: pass
    return s


def _detect_column_type(values: list) -> str:
    """Infer SQLite type from a list of raw (possibly string) values."""
    if not values:
        return "TEXT"
    coerced = [_coerce_value(v) for v in values if v is not None]
    if not coerced:
        return "TEXT"
    if all(isinstance(v, bool) for v in coerced):
        return "INTEGER"
    if all(isinstance(v, int) and not isinstance(v, bool) for v in coerced):
        return "INTEGER"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in coerced):
        return "REAL"
    return "TEXT"


def build_sqlite_from_tables(tables: dict) -> sqlite3.Connection:
    """Build an in-memory SQLite DB from tables dict, coercing string numerics to REAL/INTEGER."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    for tname, rows in tables.items():
        if not rows:
            continue
        col_names = list(rows[0].keys())
        # Scan all rows to infer type per column
        col_types = {}
        for c in col_names:
            col_types[c] = _detect_column_type([r.get(c) for r in rows])
        cols_sql = [f'"{c}" {col_types[c]}' for c in col_names]
        cur.execute(f'CREATE TABLE "{tname}" ({", ".join(cols_sql)})')
        placeholders = ", ".join(["?"] * len(col_names))
        cur.executemany(
            f'INSERT INTO "{tname}" VALUES ({placeholders})',
            [tuple(_coerce_value(r.get(c)) for c in col_names) for r in rows]
        )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Column statistics (the key artifact of M1)
# ---------------------------------------------------------------------------

def _fk_hint(col: str, table_names: set) -> str:
    if not col.startswith("id_"):
        return ""
    target = col[3:]
    if target in table_names:
        return f" [FK -> {target}.id]"
    if f"{target}s" in table_names:
        return f" [FK -> {target}s.id]"
    return ""


def compute_column_stats(tables: dict) -> str:
    """Generate a compact stats block per table+column.

    Coerces string-encoded numerics before computing stats.
    For numeric: type + range + mean (+ FK hint).
    For text:    cardinality + 3 samples (+ ISO-date hint).
    """
    lines = []
    table_names = set(tables.keys())
    for tname, rows in tables.items():
        if not rows:
            continue
        lines.append(f"Table {tname} ({len(rows)} rows):")
        for col in rows[0].keys():
            raw_values = [r[col] for r in rows if r.get(col) is not None]
            if not raw_values:
                lines.append(f"  {col}: (empty)")
                continue
            ctype = _detect_column_type(raw_values)
            coerced = [_coerce_value(v) for v in raw_values]
            fk = _fk_hint(col, table_names)

            if ctype in ("INTEGER", "REAL"):
                nums = [float(v) for v in coerced if isinstance(v, (int, float)) and not isinstance(v, bool)]
                if not nums:
                    lines.append(f"  {col} {ctype}{fk}")
                    continue
                mn, mx, avg = min(nums), max(nums), sum(nums) / len(nums)
                card = len(set(nums))
                pk_tag = " PK" if col == "id" else ""
                fmt = "{:.0f}" if ctype == "INTEGER" else "{:.2f}"
                lines.append(
                    f"  {col} {ctype}{pk_tag}{fk}, range=[{fmt.format(mn)}, {fmt.format(mx)}], "
                    f"mean={avg:.2f}, cardinality={card}"
                )
            else:
                uniq = list(dict.fromkeys(str(v) for v in coerced))
                card = len(uniq)
                sample = ", ".join(uniq[:3])
                date_tag = " (ISO date)" if re.match(r"^\d{4}-\d{2}-\d{2}", str(coerced[0])) else ""
                lines.append(f"  {col} TEXT{date_tag}{fk}, cardinality={card}, samples=[{sample}]")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------

def build_payload_full(tables: dict, meta: dict) -> str:
    """Full TCF L3 data — what we've been sending in Phase 1-6."""
    mp, dd = _write_fixture(tables, meta)
    data_text = tcf_encode(str(mp), str(dd), EncodeConfig(level=3, include_stats=False))
    return "## Dados (TCF L3)\n" + data_text


def build_payload_schema(tables: dict, meta: dict) -> str:
    """Minimal: column names and types (type-coerced from string-encoded values)."""
    lines = ["## Schema"]
    table_names = set(tables.keys())
    for tname, rows in tables.items():
        if not rows:
            continue
        lines.append(f"\nTable {tname} ({len(rows)} rows):")
        for col in rows[0].keys():
            raw_values = [r.get(col) for r in rows]
            t = _detect_column_type(raw_values)
            lines.append(f"  {col} {t}{_fk_hint(col, table_names)}")
    return "\n".join(lines)


def build_payload_stats(tables: dict, meta: dict) -> str:
    """Schema + column statistics (the H-TCF2 hypothesis payload)."""
    return "## Schema + Stats\n" + compute_column_stats(tables)


VARIANTS = {
    "sql_full": build_payload_full,
    "sql_schema": build_payload_schema,
    "sql_stats": build_payload_stats,
}


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = """Voce e um analista de dados. Dado o schema abaixo, gere UMA query SQLite SQL que responda a pergunta. Responda APENAS com a SQL em um bloco ```sql ... ```, sem explicacao.

{payload}

## Pergunta
{question}

## SQL
"""


# ---------------------------------------------------------------------------
# SQL extraction + scoring
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)

def extract_sql(response: str) -> str:
    """Extract SQL from LLM response. Prefers fenced block."""
    if not response:
        return ""
    m = _FENCE_RE.search(response)
    if m:
        return m.group(1).strip()
    # Fallback: keep lines that look like SQL (skip comments and markdown)
    keep = []
    for line in response.strip().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("```"):
            continue
        keep.append(s)
    return "\n".join(keep).strip()


def score_sql(q: dict, sql: str, conn: sqlite3.Connection, gt: dict) -> tuple[bool, str, str]:
    """Execute SQL and compare to GT. Returns (ok, reason, executed_result_str)."""
    if not sql:
        return False, "empty_sql", ""
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
    except sqlite3.Error as e:
        return False, f"sql_error:{type(e).__name__}", str(e)[:120]

    if not rows:
        return False, "no_rows", "[]"

    # Expect scalar or single-col result in first cell
    cell = rows[0][0] if rows[0] else None
    expected = gt[q["key"]]

    if q["type"] == "string":
        ok = str(expected).lower() in str(cell).lower() if cell is not None else False
        return ok, "correct" if ok else "wrong_name", str(cell)

    try:
        val = float(cell)
    except (TypeError, ValueError):
        return False, "result_not_numeric", str(cell)

    if q["type"] == "count":
        ok = int(round(val)) == int(expected)
        return ok, "correct" if ok else "wrong_count", str(int(round(val)))

    tol = max(abs(float(expected)) * 0.02, 0.5)
    ok = abs(val - float(expected)) <= tol
    return ok, "correct" if ok else "arithmetic_error", f"{val:.2f}"


# ---------------------------------------------------------------------------
# Runner
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
        if r.get("reason") == "exception":
            continue
        out.add(r["key"])
    return out


def run_m1(models: list[str], n_orders: int, variants: list[str], endpoint: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    tables, meta = retail_sales(n_orders=n_orders, seed=42)
    gt = _compute_gt(tables)
    conn = build_sqlite_from_tables(tables)

    # Pre-build payloads once (fixed for all models)
    payloads = {v: VARIANTS[v](tables, meta) for v in variants}
    for v, p in payloads.items():
        print(f"  payload[{v}] = {len(p)} chars")

    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    combos: list[dict] = []
    for model in models:
        for variant in variants:
            for q_name, q in QUESTIONS.items():
                key = f"m1|{model}|{variant}|n{n_orders}|{q_name}"
                if key in completed:
                    continue
                prompt = PROMPT_TEMPLATE.format(payload=payloads[variant], question=q["text"])
                combos.append({
                    "key": key, "model": model, "variant": variant,
                    "question": q, "q_name": q_name, "prompt": prompt,
                })

    print(f"\n[M1] {len(models)} models x {len(variants)} variants x {len(QUESTIONS)} q")
    print(f"     {len(combos)} to run, {len(completed)} cached\n")

    t_start = time.time()
    warmed: set[str] = set()

    for i, c in enumerate(combos, 1):
        model = c["model"]
        if model not in warmed:
            print(f"  warming {model} ...")
            try:
                client.generate(model, "ok", options={**LLM_OPTIONS, "num_predict": 2, "think": False}, timeout=300)
            except Exception as e:
                print(f"  warm failed: {e}", file=sys.stderr)
            warmed.add(model)

        elapsed = time.time() - t_start
        print(f"  [{i}/{len(combos)} el={elapsed:.0f}s] {c['key']}", end=" ", flush=True)

        call_options = dict(LLM_OPTIONS)
        # For toggle-capable models, default to no-think for SQL (faster, cleaner output)
        call_options["think"] = False

        response, ok, reason, executed, sql, total_ms = "", False, "exception", "", "", 0
        for attempt in (1, 2):
            try:
                result = client.generate(model, c["prompt"], options=call_options)
                response = result["text"]
                total_ms = result.get("total_duration_ns", 0) // 1_000_000
                sql = extract_sql(response)
                ok, reason, executed = score_sql(c["question"], sql, conn, gt)
                print(f"{'OK' if ok else 'NO'} ({reason}) sql_len={len(sql)} -> {executed[:40]}")
                break
            except Exception as e:
                es = str(e)
                transient = any(x in es for x in ("RemoteDisconnected", "ConnectionError", "ConnectionAborted", "ReadTimeout"))
                if transient and attempt == 1:
                    print(f"TRANSIENT ({type(e).__name__}); sleeping 15s...", flush=True)
                    time.sleep(15)
                    continue
                print(f"ERROR: {e}")
                response = f"ERROR:{e}"
                break

        record = {
            "key": c["key"], "phase": "m1", "model": model,
            "variant": c["variant"], "question": c["q_name"],
            "question_key": c["question"]["key"],
            "response": response, "sql": sql, "executed_result": executed,
            "ok": ok, "reason": reason,
            "expected": str(gt[c["question"]["key"]]),
            "prompt_chars": len(c["prompt"]),
            "n_orders": n_orders,
            "total_ms": total_ms,
        }
        with open(manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    conn.close()
    print_summary(manifest_path)


def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M1] No records.")
        return
    records = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not records:
        print("[M1] Empty manifest.")
        return

    print(f"\n=== M1 Summary ({len(records)} records) ===\n")

    # Per (model, variant)
    by_mv = defaultdict(lambda: {"ok": 0, "total": 0, "chars": 0})
    for r in records:
        k = (r["model"], r["variant"])
        by_mv[k]["total"] += 1
        by_mv[k]["chars"] = max(by_mv[k]["chars"], r.get("prompt_chars", 0))
        if r["ok"]:
            by_mv[k]["ok"] += 1

    print(f"  {'Model':<22} {'Variant':<14} {'OK/N':<8}  {'Chars':<7}  Acc%")
    print(f"  {'-'*22} {'-'*14} {'-'*8}  {'-'*7}  ----")
    for (m, v), d in sorted(by_mv.items()):
        pct = d['ok'] / d['total'] * 100 if d['total'] else 0
        print(f"  {m:<22} {v:<14} {d['ok']}/{d['total']:<6}  {d['chars']:<7}  {pct:>4.0f}%")

    # Per (variant, question) — shows which questions each variant unlocks
    print(f"\n  Per-question breakdown (aggregated across models):")
    by_vq = defaultdict(lambda: {"ok": 0, "total": 0})
    for r in records:
        k = (r["variant"], r["question"])
        by_vq[k]["total"] += 1
        if r["ok"]:
            by_vq[k]["ok"] += 1
    variants_order = sorted(set(k[0] for k in by_vq.keys()))
    questions_order = list(QUESTIONS.keys())
    header = f"  {'Question':<18} " + " ".join(f"{v:>10}" for v in variants_order)
    print(header)
    for q in questions_order:
        row = f"  {q:<18} "
        for v in variants_order:
            d = by_vq.get((v, q), {"ok": 0, "total": 0})
            if d["total"]:
                row += f" {d['ok']}/{d['total']:<4}  "
            else:
                row += f"   -     "
        print(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="M1 - Code generation probe (TCF -> SQL -> SQLite)")
    parser.add_argument("--models", nargs="+", default=[
        "qwen2.5-coder:7b", "phi4:latest", "qwen3:14b",
    ])
    parser.add_argument("--variants", nargs="+", default=None,
                        choices=list(VARIANTS.keys()))
    parser.add_argument("--n-orders", type=int, default=100)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    variants = args.variants or list(VARIANTS.keys())

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    if args.dry_run:
        tables, meta = retail_sales(n_orders=args.n_orders, seed=42)
        for v in variants:
            payload = VARIANTS[v](tables, meta)
            prompt = PROMPT_TEMPLATE.format(payload=payload, question=QUESTIONS["q_sum"]["text"])
            print(f"\n{'='*60}\n=== {v}  ({len(payload)} chars payload, {len(prompt)} chars total prompt)\n{'='*60}")
            print(prompt[:1200])
            if len(prompt) > 1200:
                print(f"\n... [{len(prompt)-1200} more chars]")
        return

    run_m1(args.models, args.n_orders, variants, args.endpoint)


if __name__ == "__main__":
    main()
