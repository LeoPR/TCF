"""L3 aliasing — @A vs integer index for dict encoding.

Tests whether models parse dict references better when encoded as letter
symbols (@A, @B, @C) vs integers (0, 1, 2).

Hypothesis: small models confuse integer dict indices with counts.
@A-style symbols signal "this is a reference" rather than "this is a number".

Cost: @A is 2 BPE tokens vs 1 for `0` -> L3 in alias mode is ~5-10% more
expensive in tokens. Worth it IF accuracy improves enough.

Comparison: integer index (baseline L3) vs @A alias L3.
1 model x 2 variants x 4 questions = 8 combos.

Usage:
    python experiments/eval/run_alias_bench.py --cpu-only --num-thread 24
    python experiments/eval/run_alias_bench.py --dry-run
"""

from __future__ import annotations
import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from string import ascii_uppercase

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tcf import encode as tcf_encode, EncodeConfig
from tests.fixtures import _write_fixture
from tests.fixtures.synthetic_v2 import retail_sales

from llm_eval.ollama_client import OllamaClient
from llm_eval.metrics import extract_number, strip_think


RESULTS_DIR = ROOT / "experiments" / "results" / "alias"
LLM_OPTIONS = {"temperature": 0, "seed": 42}
DEFAULT_MODELS = ["gemma3:4b"]
SCALE_DEFAULT = 50
SEED = 42


# ---------------------------------------------------------------------------
# Alias transform: rewrites L3 integer dict refs to @A, @B, @C symbols
# ---------------------------------------------------------------------------

_DICT_HEADER_RE = re.compile(r"^# dict (\S+): (.+)$")
_RLE_RE = re.compile(r"^(\d+)\*(.+)$")
_COL_HEADER_RE = re.compile(r"^(\w+):$")


def _idx_to_alias(i: int) -> str:
    """0->@A, 1->@B, ..., 25->@Z, 26->@AA, 27->@AB, ..."""
    letters = ""
    i += 1  # Excel-style, 1-indexed internally
    while i > 0:
        i, rem = divmod(i - 1, 26)
        letters = ascii_uppercase[rem] + letters
    return f"@{letters}"


def rewrite_to_alias(text: str) -> str:
    """Post-process L3 TCF text: replace integer dict indices with @A-style symbols.

    Transforms:
      # dict produto: Regua,Lapis,Borracha
      produto:
      0
      3*1
      2
    Into:
      # dict produto: @A=Regua,@B=Lapis,@C=Borracha
      produto:
      @A
      3*@B
      @C
    """
    lines = text.splitlines()
    # First pass: find dict columns and build alias maps
    dict_cols: dict[str, list[str]] = {}  # colname -> values
    for line in lines:
        m = _DICT_HEADER_RE.match(line)
        if m:
            col = m.group(1)
            vals = [v.strip() for v in m.group(2).split(",")]
            dict_cols[col] = vals

    # Second pass: rewrite
    out = []
    current_col: str | None = None
    in_dict_col = False
    for line in lines:
        # Dict header line -> rewrite to alias form
        m_dict = _DICT_HEADER_RE.match(line)
        if m_dict:
            col = m_dict.group(1)
            vals = dict_cols[col]
            parts = [f"{_idx_to_alias(i)}={v}" for i, v in enumerate(vals)]
            out.append(f"# dict {col}: {','.join(parts)}")
            continue

        # Column header line
        m_col = _COL_HEADER_RE.match(line)
        if m_col:
            current_col = m_col.group(1)
            in_dict_col = current_col in dict_cols
            out.append(line)
            continue

        # Value line inside a dict-encoded column: integer index -> @alias
        if in_dict_col and current_col:
            m_rle = _RLE_RE.match(line)
            if m_rle:
                n = m_rle.group(1)
                v = m_rle.group(2).strip()
                if v.isdigit():
                    out.append(f"{n}*{_idx_to_alias(int(v))}")
                    continue
            stripped = line.strip()
            if stripped.isdigit():
                out.append(_idx_to_alias(int(stripped)))
                continue

        # If we see a non-value line (blank, header, STATS), exit dict-col context
        if line.strip() == "" or line.startswith("#") or line.startswith("##"):
            in_dict_col = False
            current_col = None
        out.append(line)

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Questions + system prompts
# ---------------------------------------------------------------------------

SYS_INT = (
    "Voce recebera dados em formato colunar comprimido (L3). "
    "Colunas com '# dict X: val0,val1,val2' tem valores substituidos pelo indice (0,1,2...). "
    "N*val = val repetido N vezes. "
    "Para responder sobre um valor especifico, busque o indice dele no dict e conte as ocorrencias. "
    "Responda com base apenas nos dados."
)
SYS_ALIAS = (
    "Voce recebera dados em formato colunar comprimido (L3). "
    "Colunas com '# dict X: @A=val0,@B=val1,@C=val2' tem valores substituidos pelo simbolo (@A,@B,@C...). "
    "N*val = val repetido N vezes. "
    "Para responder sobre um valor especifico, busque o simbolo dele no dict e conte as ocorrencias. "
    "Responda com base apenas nos dados."
)

QUESTIONS = {
    "q_count":   {"text": "Quantas linhas existem nos dados? Responda apenas com um numero inteiro.",
                   "key": "count", "type": "count"},
    "q_top":     {"text": "Qual produto aparece mais vezes? Responda apenas com o nome do produto.",
                   "key": "top_product", "type": "string"},
    "q_distinct":{"text": "Quantos clientes distintos aparecem nos dados? Responda apenas com um numero inteiro.",
                   "key": "distinct_customers", "type": "count"},
    "q_top_cli": {"text": "Qual cliente aparece mais vezes? Responda apenas com o nome do cliente.",
                   "key": "top_customer", "type": "string"},
}


def _compute_gt(tables):
    clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
    produtos = {p["id"]: p["nome"] for p in tables["produtos"]}
    vendas = tables["vendas"]
    n = len(vendas)
    prod_counter = Counter(v["id_produto"] for v in vendas)
    cli_counter = Counter(v["id_cliente"] for v in vendas)
    top_pid = prod_counter.most_common(1)[0][0]
    top_cid = cli_counter.most_common(1)[0][0]
    return {
        "count": n,
        "top_product": produtos.get(top_pid, top_pid),
        "top_customer": clientes.get(top_cid, top_cid),
        "distinct_customers": len(set(v["id_cliente"] for v in vendas)),
    }


def _score(q, response, gt):
    expected = gt[q["key"]]
    if q["type"] == "string":
        clean = strip_think(response).strip().lower()
        ok = str(expected).lower() in clean
        return ok, "correct" if ok else "wrong_name"
    val = extract_number(response)
    if val is None:
        return False, "parse_failure"
    if q["type"] == "count":
        ok = int(round(val)) == int(expected)
        return ok, "correct" if ok else "wrong_count"
    return False, "unknown_type"


def run(models, endpoint, dry_run=False, cpu_only=False, num_thread=None, scale=SCALE_DEFAULT):
    client = OllamaClient(endpoint)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    llm_options = dict(LLM_OPTIONS)
    if cpu_only:
        llm_options["num_gpu"] = 0
    if num_thread is not None:
        llm_options["num_thread"] = num_thread

    completed = set()
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try: completed.add(json.loads(line)["key"])
                except: pass

    print(f"[Alias] scale={scale}")
    tables, meta = retail_sales(n_orders=scale, seed=SEED)
    gt = _compute_gt(tables)
    mp, dd = _write_fixture(tables, meta)

    # L3 base (integer dict)
    l3_int = tcf_encode(str(mp), str(dd), EncodeConfig(level=3, include_stats=False))
    # L3 alias (@A-style)
    l3_alias = rewrite_to_alias(l3_int)

    variants = {
        "integer": (SYS_INT, l3_int),
        "alias":   (SYS_ALIAS, l3_alias),
    }

    print(f"[Alias] L3 integer: {len(l3_int):>6} chars")
    print(f"[Alias] L3 alias:   {len(l3_alias):>6} chars  delta={len(l3_alias)-len(l3_int):+d}")
    print(f"[Alias] GT: {gt}")
    n_combos = len(models) * len(variants) * len(QUESTIONS)
    print(f"[Alias] {n_combos} combos ({len(completed)} cached)")

    if dry_run:
        print("\n--- integer variant (first 30 lines) ---")
        print("\n".join(l3_int.splitlines()[:30]))
        print("\n--- alias variant (first 30 lines) ---")
        print("\n".join(l3_alias.splitlines()[:30]))
        return

    warmed = set()
    t_start = time.time()
    i = 0
    for model in models:
        for variant_name, (sys_prompt, data_text) in variants.items():
            for q_name, q in QUESTIONS.items():
                key = f"{model}|{variant_name}|{q_name}"
                if key in completed:
                    continue
                i += 1
                prompt = f"{sys_prompt}\n\n{q['text']}\n\n{data_text}"

                if model not in warmed:
                    print(f"  warming {model}...")
                    wopts = {"num_predict": 2}
                    if cpu_only: wopts["num_gpu"] = 0
                    if num_thread: wopts["num_thread"] = num_thread
                    try:
                        client.generate(model, "ok", options=wopts)
                        warmed.add(model)
                    except Exception as e:
                        print(f"  warm failed: {e}", file=sys.stderr)

                el = time.time() - t_start
                print(f"  [{i}/{n_combos} el={el:.0f}s] {model} {variant_name} {q_name}", end=" ", flush=True)
                try:
                    result = client.generate(model, prompt, options=llm_options)
                    response = result["text"]
                    ok, reason = _score(q, response, gt)
                    print(f"{'OK' if ok else 'NO'} ({reason}) ans={response[:40]!r}")
                except Exception as e:
                    print(f"ERROR: {e}")
                    response, ok, reason = f"ERROR:{e}", False, "exception"
                    result = {"prompt_tokens": 0, "response_tokens": 0, "total_duration_ns": 0}

                record = {
                    "key": key, "model": model, "variant": variant_name, "question": q_name,
                    "response": response, "ok": ok, "reason": reason,
                    "expected": gt[q["key"]],
                    "prompt_tokens": result.get("prompt_tokens", 0),
                    "response_tokens": result.get("response_tokens", 0),
                    "total_ms": result.get("total_duration_ns", 0) // 1_000_000,
                }
                with open(manifest_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    print()
    print("=" * 60)
    print(f"{'model':<22} {'variant':<10} acc")
    by = defaultdict(list)
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        r = json.loads(line)
        by[(r["model"], r["variant"])].append(r["ok"])
    for (m, v), oks in sorted(by.items()):
        n, c_ok = len(oks), sum(oks)
        print(f"{m:<22} {v:<10} {c_ok/n*100:>4.0f}%  ({c_ok}/{n})")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    p.add_argument("--endpoint", default="http://localhost:11434")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--cpu-only", action="store_true")
    p.add_argument("--num-thread", type=int, default=None)
    p.add_argument("--scale", type=int, default=SCALE_DEFAULT,
                   help=f"retail_sales n_orders (default {SCALE_DEFAULT})")
    a = p.parse_args()
    run(a.models, a.endpoint, dry_run=a.dry_run,
        cpu_only=a.cpu_only, num_thread=a.num_thread, scale=a.scale)


if __name__ == "__main__":
    main()
