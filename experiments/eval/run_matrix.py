"""P06 -- Phased evaluation pipeline with progressive ablation.

Invocation:
    python -m experiments.eval discover
    python -m experiments.eval phase0
    python -m experiments.eval phase1 --models auto
    python -m experiments.eval phase2
    python -m experiments.eval phase3
    python -m experiments.eval status

Each phase is idempotent: interrupt and resume at any time.
Results from each phase feed into the next via survivors/top_configs files.
"""

from __future__ import annotations
import argparse
import csv as csv_mod
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

# ---------------------------------------------------------------------------
# Path setup — allow import of src/tcf without pip install
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tcf import encode as tcf_encode, decode as tcf_decode, EncoderConfig

from llm_eval.ollama_client import OllamaClient
from llm_eval.formats import format_csv, format_jsonl, format_tcf
from llm_eval.ground_truth import compute as compute_gt, vl_plain_list
from llm_eval.metrics import score_response, score_decode
from llm_eval.prompts import (
    build_prompt,
    list_questions_by_layer,
    QUESTION_DEFS,
)
from llm_eval.models import fetch_local_models, auto_select_models

DATA_DIR = ROOT / "data"
META = DATA_DIR / "metadata.json"
RESULTS_ROOT = ROOT / "experiments" / "results"

# Ground truth — computed once, always in sync with source CSVs
GROUND_TRUTH = compute_gt(DATA_DIR)

# Formats tested in Phase 1
PHASE1_FORMATS = ["csv", "jsonl", "tcf"]

# TCF variant dimensions (Phase 2)
NUMERIC_MODES = ["raw_float", "int_scaled", "bins_16"]
FK_MODES = ["id_raw", "dict", "hint", "inline"]
SORTED_OPTS = [True, False]

# Vision model families to exclude from text-only evaluation
VISION_FAMILIES = {"mllama", "qwen3vl", "llava", "moondream"}


# =========================================================================
# Data cache
# =========================================================================

class DataCache:
    """Cache formatted data blocks to avoid repeated encoding."""

    def __init__(self) -> None:
        self._flat: dict[str, str] = {}
        self._tcf: dict[tuple, str] = {}
        self._rows: list[dict] | None = None
        self._vl_list: str | None = None

    def _load_expanded(self) -> list[dict]:
        if self._rows is not None:
            return self._rows
        pessoas = {
            r["id"]: r["nome"]
            for r in csv_mod.DictReader(
                (DATA_DIR / "pessoas.csv").open(encoding="utf-8")
            )
        }
        produtos = {
            r["id"]: r["nome"]
            for r in csv_mod.DictReader(
                (DATA_DIR / "produtos.csv").open(encoding="utf-8")
            )
        }
        rows = []
        for r in csv_mod.DictReader(
            (DATA_DIR / "vendas.csv").open(encoding="utf-8")
        ):
            rows.append({
                "pessoa": pessoas.get(r["id_pessoa"], r["id_pessoa"]),
                "produto": produtos.get(r["id_produto"], r["id_produto"]),
                "vl": float(r["vl"]),
            })
        self._rows = rows
        return rows

    def csv(self) -> str:
        if "csv" not in self._flat:
            self._flat["csv"] = format_csv(self._load_expanded())
        return self._flat["csv"]

    def jsonl(self) -> str:
        if "jsonl" not in self._flat:
            self._flat["jsonl"] = format_jsonl(self._load_expanded())
        return self._flat["jsonl"]

    def tcf(
        self,
        numeric: str = "raw_float",
        fk_mode: str = "id_raw",
        include_sorted: bool = True,
        include_stats: bool = False,
    ) -> str:
        key = (numeric, fk_mode, include_sorted, include_stats)
        if key not in self._tcf:
            cfg = EncoderConfig(
                numeric=numeric, fk_mode=fk_mode,
                include_sorted=include_sorted,
                include_stats=include_stats,
            )
            raw = tcf_encode(META, DATA_DIR, config=cfg)
            self._tcf[key] = format_tcf(raw)
        return self._tcf[key]

    def vl_list(self) -> str:
        if self._vl_list is None:
            self._vl_list = vl_plain_list(DATA_DIR)
        return self._vl_list

    def get(
        self,
        fmt: str,
        numeric: str | None = None,
        fk_mode: str | None = None,
        include_sorted: bool = True,
        include_stats: bool = False,
    ) -> str:
        if fmt == "csv":
            return self.csv()
        if fmt == "jsonl":
            return self.jsonl()
        if fmt == "tcf":
            return self.tcf(
                numeric or "raw_float", fk_mode or "id_raw",
                include_sorted, include_stats,
            )
        raise ValueError(f"Unknown format: {fmt}")


# =========================================================================
# Manifest (idempotent tracking)
# =========================================================================

def _run_key(combo: dict[str, Any]) -> str:
    parts = [
        combo.get("model", ""),
        combo.get("format", ""),
        combo.get("numeric") or "N",
        combo.get("fk_mode") or "N",
        str(combo.get("include_sorted", "N")),
        str(combo.get("include_stats", "N")),
        combo.get("layer", ""),
        combo.get("question", ""),
    ]
    return "|".join(parts)


def _load_manifest(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                keys.add(json.loads(line)["key"])
            except (json.JSONDecodeError, KeyError):
                pass
    return keys


def _append_manifest(path: Path, combo: dict[str, Any], result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "key": _run_key(combo),
        **{k: combo.get(k) for k in ("model", "format", "numeric", "fk_mode", "include_sorted", "include_stats", "layer", "question")},
        "correct": result.get("correct", False),
        "timestamp": time.time(),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _append_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


# =========================================================================
# Single-run executor
# =========================================================================

def _score_safe(question_key: str, response: str) -> tuple[bool, str]:
    """Score a response, returning (correct, error_type)."""
    try:
        gt_key = QUESTION_DEFS[question_key]["key"]
        expected = GROUND_TRUTH[gt_key]
        return score_response(response, expected, gt_key)
    except (KeyError, ValueError, TypeError):
        return False, "no_ground_truth"


def _score_decode_safe(response: str) -> bool:
    try:
        return score_decode(response, GROUND_TRUTH["vl_values"])["correct"]
    except (KeyError, ValueError):
        return False


# Default Ollama options for reproducibility.
# temperature=0 for deterministic outputs; can be overridden per-phase.
DEFAULT_OPTIONS: dict[str, Any] = {
    "temperature": 0,
    "seed": 42,
}


def run_single(
    combo: dict[str, Any],
    client: OllamaClient,
    cache: DataCache,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one (model, format, config, question) combination."""
    model = combo["model"]
    layer = combo["layer"]
    question = combo["question"]
    fmt = combo.get("format", "none")
    numeric = combo.get("numeric")
    fk_mode = combo.get("fk_mode")
    include_sorted = combo.get("include_sorted", True)
    include_stats = combo.get("include_stats", False)

    llm_options = dict(DEFAULT_OPTIONS)
    if options:
        llm_options.update(options)

    result: dict[str, Any] = dict(combo)
    result["temperature"] = llm_options.get("temperature", 0)

    try:
        # Build prompt
        if layer == "math_control":
            prompt = build_prompt("math_control", "", question, vl_list=cache.vl_list())
        else:
            data_block = cache.get(fmt, numeric, fk_mode, include_sorted, include_stats)
            prompt = build_prompt(fmt, data_block, question)

        # Call LLM
        t0 = time.perf_counter()
        gen = client.generate(model=model, prompt=prompt, options=llm_options)
        latency = time.perf_counter() - t0
        response = gen["text"].strip()

        # Score
        if layer == "decode_only":
            correct = _score_decode_safe(response)
            error_type = "correct" if correct else "decode_error"
        else:
            correct, error_type = _score_safe(question, response)

        result.update({
            "response": response,
            "correct": correct,
            "error_type": error_type,
            "latency_s": round(latency, 4),
            "prompt_chars": len(prompt),
            "prompt_tokens": gen.get("prompt_tokens", 0),
            "response_tokens": gen.get("response_tokens", 0),
            # Ollama detailed timing (nanoseconds -> seconds)
            "total_duration_s": round(gen.get("total_duration_ns", 0) / 1e9, 4),
            "load_duration_s": round(gen.get("load_duration_ns", 0) / 1e9, 4),
            "prompt_eval_s": round(gen.get("prompt_eval_ns", 0) / 1e9, 4),
            "eval_s": round(gen.get("eval_ns", 0) / 1e9, 4),
            "done_reason": gen.get("done_reason", ""),
            "error": None,
        })

    except Exception as exc:
        result.update({
            "response": "",
            "correct": False,
            "error_type": "exception",
            "latency_s": 0,
            "prompt_chars": 0,
            "prompt_tokens": 0,
            "response_tokens": 0,
            "total_duration_s": 0,
            "load_duration_s": 0,
            "prompt_eval_s": 0,
            "eval_s": 0,
            "done_reason": "",
            "error": str(exc)[:300],
        })

    return result


# =========================================================================
# Generic phase runner
# =========================================================================

def _run_phase(
    combos: list[dict[str, Any]],
    phase_dir: Path,
    client: OllamaClient,
    cache: DataCache,
    label: str = "phase",
) -> list[dict[str, Any]]:
    """Run a list of combinations idempotently. Returns all results (including cached)."""

    manifest_path = phase_dir / "manifest.jsonl"
    results_dir = phase_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    completed_keys = _load_manifest(manifest_path)
    print(f"[{label}] {len(combos)} combinations, {len(completed_keys)} already done")

    all_results: list[dict[str, Any]] = []
    new_count = 0
    skip_count = 0
    _warmed_up: set[str] = set()

    for i, combo in enumerate(combos, 1):
        key = _run_key(combo)
        if key in completed_keys:
            skip_count += 1
            continue

        model = combo["model"]

        # Warmup: one trivial call per model to absorb load_duration
        if model not in _warmed_up:
            print(f"  [warmup] {model} ... ", end="", flush=True)
            try:
                client.generate(model=model, prompt="2+2=?")
                print("ready")
            except Exception as e:
                print(f"warmup failed: {e}")
            _warmed_up.add(model)
        tag = f"[{i}/{len(combos)}]"
        short = f"{combo.get('layer','')}/{combo.get('question','')}"
        fmt_tag = combo.get("format", "")
        if combo.get("numeric"):
            fmt_tag += f"/{combo['numeric']}"
        if combo.get("fk_mode"):
            fmt_tag += f"/{combo['fk_mode']}"

        print(f"  {tag} {model} {fmt_tag} {short} ... ", end="", flush=True)

        try:
            result = run_single(combo, client, cache)
        except KeyboardInterrupt:
            print("\n[interrupted] progress saved in manifest")
            sys.exit(0)

        # Persist immediately
        _append_manifest(manifest_path, combo, result)
        slug = model.replace(":", "_").replace("/", "_")
        _append_result(results_dir / f"{slug}.jsonl", result)

        completed_keys.add(key)
        all_results.append(result)
        new_count += 1

        status = "OK" if result["correct"] else "FAIL"
        print(status)

    print(f"[{label}] done: {new_count} new, {skip_count} cached")
    return all_results


# =========================================================================
# Phase 0 — Reversibility gate (no LLM calls)
# =========================================================================

def cmd_phase0(args: argparse.Namespace) -> None:
    """Verify encode -> decode reversibility for all config variants."""
    import pytest as _  # just to check it exists

    phase_dir = RESULTS_ROOT / "phase0"
    phase_dir.mkdir(parents=True, exist_ok=True)

    orig_vendas = list(csv_mod.DictReader(
        (DATA_DIR / "vendas.csv").open(encoding="utf-8")
    ))
    orig_vl = [float(r["vl"]) for r in orig_vendas]
    n = len(orig_vendas)

    results: list[dict] = []

    configs = [
        ("raw_float/id_raw/sorted",   EncoderConfig()),
        ("raw_float/id_raw/nosorted",  EncoderConfig(include_sorted=False)),
        ("int_scaled/id_raw/sorted",   EncoderConfig(numeric="int_scaled", int_scale=100)),
        ("bins_16/id_raw/sorted",      EncoderConfig(numeric="bins_16", n_bins=16)),
        ("raw_float/dict/sorted",      EncoderConfig(fk_mode="dict")),
        ("raw_float/hint/sorted",      EncoderConfig(fk_mode="hint")),
        ("raw_float/inline/sorted",    EncoderConfig(fk_mode="inline")),
    ]

    all_pass = True
    for name, cfg in configs:
        tcf_text = tcf_encode(META, DATA_DIR, config=cfg)
        tables = tcf_decode(tcf_text)
        restored = tables.get("vendas", [])

        ok = len(restored) == n
        max_diff = 0.0
        if ok:
            for orig_row, rest_row in zip(orig_vendas, restored):
                try:
                    diff = abs(float(orig_row["vl"]) - float(rest_row["vl"]))
                    max_diff = max(max_diff, diff)
                except (ValueError, KeyError):
                    ok = False
                    break

        # Tolerance depends on encoding
        if cfg.numeric == "bins_16":
            tol = (max(orig_vl) - min(orig_vl)) / cfg.n_bins  # one full bin width
        elif cfg.numeric == "int_scaled":
            tol = 1.0 / cfg.int_scale + 1e-9
        else:
            tol = 1e-6

        passed = ok and max_diff <= tol
        all_pass = all_pass and passed
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name:40s}  rows={len(restored)}  max_diff={max_diff:.6f}  tol={tol:.6f}")

        results.append({
            "config": name,
            "rows_ok": len(restored) == n,
            "max_diff": max_diff,
            "tolerance": tol,
            "passed": passed,
        })

    out = phase_dir / "reversibility.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n[phase0] {'ALL PASS' if all_pass else 'SOME FAILED'} -> {out}")
    if not all_pass:
        sys.exit(1)


# =========================================================================
# Phase 1 — Basic formats x all models (H02 + H03)
# =========================================================================

def _resolve_models(
    raw: list[str],
    endpoint: str,
    desired: int = 6,
) -> list[str]:
    """Resolve 'auto' into actual model names from Ollama.

    Returns models ordered by parameter size (smallest first) so that:
    - Fastest models run first (quick feedback)
    - GPU swap overhead is minimized (small models load faster)
    - If interrupted, the most results are from fast models
    """
    if raw == ["auto"]:
        all_models = fetch_local_models(endpoint)
        # Filter out vision models
        text_models = [
            m for m in all_models
            if m.get("family") not in VISION_FAMILIES
        ]
        names, picks = auto_select_models(text_models, desired=desired)
        # Sort by parameter size: smallest (fastest) first
        param_order = sorted(
            zip(names, picks),
            key=lambda x: x[1].get("param_float", 0),
        )
        names = [n for n, _ in param_order]
        print(f"[auto-discovery] selected {len(names)} models (smallest first): {names}")
        return names
    return raw


def _phase1_combos(models: list[str]) -> list[dict[str, Any]]:
    combos: list[dict[str, Any]] = []
    mc_qs = list(list_questions_by_layer("math_control").keys())
    compute_qs = list(list_questions_by_layer("compute").keys())

    for model in models:
        # math_control (once per model, no format)
        for q in mc_qs:
            combos.append({
                "model": model, "format": "none",
                "numeric": None, "fk_mode": None, "include_sorted": None,
                "layer": "math_control", "question": q,
            })
        for fmt in PHASE1_FORMATS:
            # decode_only
            combos.append({
                "model": model, "format": fmt,
                "numeric": "raw_float" if fmt == "tcf" else None,
                "fk_mode": "id_raw" if fmt == "tcf" else None,
                "include_sorted": True if fmt == "tcf" else None,
                "layer": "decode_only", "question": "decode_vl",
            })
            # compute
            for q in compute_qs:
                combos.append({
                    "model": model, "format": fmt,
                    "numeric": "raw_float" if fmt == "tcf" else None,
                    "fk_mode": "id_raw" if fmt == "tcf" else None,
                    "include_sorted": True if fmt == "tcf" else None,
                    "layer": "compute", "question": q,
                })
    return combos


def _compute_accuracy(manifest_path: Path, model: str, layer: str) -> float:
    """Compute accuracy for a (model, layer) pair from the manifest."""
    total = 0
    correct = 0
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("model") == model and entry.get("layer") == layer:
            total += 1
            if entry.get("correct"):
                correct += 1
    return correct / total if total > 0 else 0.0


def cmd_phase1(args: argparse.Namespace) -> None:
    """Phase 1: basic formats x all models."""
    endpoint = args.endpoint
    client = OllamaClient(endpoint)
    if not client.is_available():
        print(f"[ERROR] Ollama not available at {endpoint}", file=sys.stderr)
        sys.exit(1)

    models = _resolve_models(args.models, endpoint, desired=args.desired_models)
    phase_dir = RESULTS_ROOT / "phase1"
    cache = DataCache()

    combos = _phase1_combos(models)
    _run_phase(combos, phase_dir, client, cache, label="phase1")

    # Compute summary
    manifest_path = phase_dir / "manifest.jsonl"
    summary: dict[str, dict[str, float]] = {}
    for model in models:
        summary[model] = {
            "math_control": _compute_accuracy(manifest_path, model, "math_control"),
            "decode_only": _compute_accuracy(manifest_path, model, "decode_only"),
            "compute": _compute_accuracy(manifest_path, model, "compute"),
        }

    # Print summary table (by model x layer)
    print("\n[PHASE 1 SUMMARY — Model x Layer]")
    print(f"  {'Model':30s} {'math':>6s} {'decode':>7s} {'compute':>8s}")
    print("  " + "-" * 55)
    for model, accs in sorted(summary.items(), key=lambda x: -x[1]["compute"]):
        print(f"  {model:30s} {accs['math_control']:6.1%} {accs['decode_only']:7.1%} {accs['compute']:8.1%}")

    # Compute accuracy by format (compute layer only)
    fmt_totals: dict[str, list[bool]] = defaultdict(list)
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        if e.get("layer") == "compute":
            fmt_totals[e.get("format", "none")].append(e.get("correct", False))

    print("\n[PHASE 1 SUMMARY — Format x Compute Accuracy]")
    print(f"  {'Format':10s} {'Accuracy':>9s} {'N':>5s}")
    print("  " + "-" * 28)
    for fmt, vals in sorted(fmt_totals.items(), key=lambda x: -sum(x[1]) / max(len(x[1]), 1)):
        acc = sum(vals) / max(len(vals), 1)
        print(f"  {fmt:10s} {acc:9.1%} {len(vals):5d}")

    # Save summary
    (phase_dir / "summary.json").write_text(
        json.dumps({
            "by_model": summary,
            "by_format": {f: sum(v) / max(len(v), 1) for f, v in fmt_totals.items()},
        }, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Filter survivors: compute accuracy >= threshold OR top-N
    threshold = args.survivor_threshold
    ranked = sorted(summary.items(), key=lambda x: -x[1]["compute"])
    survivors = [m for m, a in ranked if a["compute"] >= threshold]
    if len(survivors) < 2:
        survivors = [m for m, _ in ranked[:max(2, args.top_survivors)]]

    (phase_dir / "survivors.json").write_text(
        json.dumps({"threshold": threshold, "survivors": survivors}, indent=2),
        encoding="utf-8",
    )
    print(f"\n[survivors] {len(survivors)} models pass to Phase 2: {survivors}")


# =========================================================================
# Phase 2 — TCF variants (H04 + H05 + H06)
# =========================================================================

def _load_survivors() -> list[str]:
    path = RESULTS_ROOT / "phase1" / "survivors.json"
    if not path.exists():
        print("[ERROR] No survivors.json found. Run phase1 first.", file=sys.stderr)
        sys.exit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["survivors"]


def _phase2_combos(models: list[str]) -> list[dict[str, Any]]:
    combos: list[dict[str, Any]] = []
    compute_qs = list(list_questions_by_layer("compute").keys())

    for model in models:
        for numeric in NUMERIC_MODES:
            for fk_mode in FK_MODES:
                for sorted_opt in SORTED_OPTS:
                    for q in compute_qs:
                        combos.append({
                            "model": model,
                            "format": "tcf",
                            "numeric": numeric,
                            "fk_mode": fk_mode,
                            "include_sorted": sorted_opt,
                            "layer": "compute",
                            "question": q,
                        })
    return combos


def cmd_phase2(args: argparse.Namespace) -> None:
    """Phase 2: TCF encoding variants x survivor models."""
    endpoint = args.endpoint
    client = OllamaClient(endpoint)
    if not client.is_available():
        print(f"[ERROR] Ollama not available at {endpoint}", file=sys.stderr)
        sys.exit(1)

    if args.models and args.models != ["auto"]:
        models = args.models
    else:
        models = _load_survivors()
    print(f"[phase2] models: {models}")

    phase_dir = RESULTS_ROOT / "phase2"
    cache = DataCache()

    combos = _phase2_combos(models)
    _run_phase(combos, phase_dir, client, cache, label="phase2")

    # Ablation analysis
    manifest_path = phase_dir / "manifest.jsonl"
    entries = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))

    # Accuracy by config
    config_acc: dict[str, list[bool]] = defaultdict(list)
    factor_acc: dict[str, dict[str, list[bool]]] = {
        "numeric": defaultdict(list),
        "fk_mode": defaultdict(list),
        "include_sorted": defaultdict(list),
    }

    for e in entries:
        cfg_key = f"{e.get('numeric','N')}/{e.get('fk_mode','N')}/{e.get('include_sorted','N')}"
        config_acc[cfg_key].append(e.get("correct", False))
        if e.get("numeric"):
            factor_acc["numeric"][e["numeric"]].append(e.get("correct", False))
        if e.get("fk_mode"):
            factor_acc["fk_mode"][e["fk_mode"]].append(e.get("correct", False))
        if e.get("include_sorted") is not None:
            factor_acc["include_sorted"][str(e["include_sorted"])].append(e.get("correct", False))

    # Rank configs
    config_ranked = sorted(
        config_acc.items(),
        key=lambda x: sum(x[1]) / max(len(x[1]), 1),
        reverse=True,
    )

    print("\n[PHASE 2 — CONFIG RANKING]")
    print(f"  {'Config':40s} {'Acc':>7s} {'N':>5s}")
    print("  " + "-" * 55)
    for cfg, vals in config_ranked[:10]:
        acc = sum(vals) / max(len(vals), 1)
        print(f"  {cfg:40s} {acc:7.1%} {len(vals):5d}")

    # Ablation: per-factor accuracy
    ablation: dict[str, dict[str, float]] = {}
    print("\n[PHASE 2 — ABLATION]")
    for factor, levels in factor_acc.items():
        ablation[factor] = {}
        print(f"  {factor}:")
        for level, vals in sorted(levels.items(), key=lambda x: -sum(x[1]) / max(len(x[1]), 1)):
            acc = sum(vals) / max(len(vals), 1)
            ablation[factor][level] = acc
            print(f"    {level:20s} {acc:7.1%} (n={len(vals)})")

    # Save
    (phase_dir / "ablation.json").write_text(
        json.dumps(ablation, indent=2, ensure_ascii=False), encoding="utf-8",
    )

    # Top configs for Phase 3
    top_n = min(3, len(config_ranked))
    top_configs = [cfg for cfg, _ in config_ranked[:top_n]]
    (phase_dir / "top_configs.json").write_text(
        json.dumps({"top_configs": top_configs}, indent=2), encoding="utf-8",
    )
    print(f"\n[top_configs] {top_configs} -> phase2/top_configs.json")

    (phase_dir / "summary.json").write_text(
        json.dumps({
            "config_ranking": {c: sum(v) / max(len(v), 1) for c, v in config_ranked},
            "ablation": ablation,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# =========================================================================
# Phase 3 — Scaling + interactions (H07, H08, H10)
# =========================================================================

def cmd_phase3(args: argparse.Namespace) -> None:
    """Phase 3: scaling tests with top models and configs."""
    endpoint = args.endpoint
    client = OllamaClient(endpoint)
    if not client.is_available():
        print(f"[ERROR] Ollama not available at {endpoint}", file=sys.stderr)
        sys.exit(1)

    # Load survivors and top configs
    models = _load_survivors()
    top_configs_path = RESULTS_ROOT / "phase2" / "top_configs.json"
    if not top_configs_path.exists():
        print("[ERROR] No top_configs.json found. Run phase2 first.", file=sys.stderr)
        sys.exit(1)
    top_configs = json.loads(top_configs_path.read_text(encoding="utf-8"))["top_configs"]

    print(f"[phase3] models: {models}")
    print(f"[phase3] top TCF configs: {top_configs}")

    phase_dir = RESULTS_ROOT / "phase3"
    cache = DataCache()
    compute_qs = list(list_questions_by_layer("compute").keys())

    # Build combos: top models x (csv + jsonl + top TCF configs) x compute questions
    combos: list[dict[str, Any]] = []
    for model in models:
        # Baseline formats
        for fmt in ["csv", "jsonl"]:
            for q in compute_qs:
                combos.append({
                    "model": model, "format": fmt,
                    "numeric": None, "fk_mode": None, "include_sorted": None,
                    "layer": "compute", "question": q,
                })
        # Top TCF configs
        for cfg_str in top_configs:
            parts = cfg_str.split("/")
            numeric = parts[0] if len(parts) > 0 and parts[0] != "N" else "raw_float"
            fk_mode = parts[1] if len(parts) > 1 and parts[1] != "N" else "id_raw"
            inc_sorted = parts[2] != "False" if len(parts) > 2 else True
            for q in compute_qs:
                combos.append({
                    "model": model, "format": "tcf",
                    "numeric": numeric, "fk_mode": fk_mode,
                    "include_sorted": inc_sorted,
                    "layer": "compute", "question": q,
                })

    _run_phase(combos, phase_dir, client, cache, label="phase3")

    # Summary: accuracy per (model, format/config)
    manifest_path = phase_dir / "manifest.jsonl"
    model_fmt_acc: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        m = e.get("model", "")
        fmt_key = e.get("format", "")
        if fmt_key == "tcf":
            fmt_key = f"tcf/{e.get('numeric','N')}/{e.get('fk_mode','N')}"
        model_fmt_acc[m][fmt_key].append(e.get("correct", False))

    print("\n[PHASE 3 SUMMARY]")
    for model in models:
        print(f"  {model}:")
        for fmt_key, vals in sorted(model_fmt_acc.get(model, {}).items()):
            acc = sum(vals) / max(len(vals), 1)
            print(f"    {fmt_key:35s} {acc:7.1%} (n={len(vals)})")

    (phase_dir / "summary.json").write_text(
        json.dumps({
            m: {f: sum(v) / max(len(v), 1) for f, v in fmts.items()}
            for m, fmts in model_fmt_acc.items()
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# =========================================================================
# discover — show available models
# =========================================================================

def cmd_discover(args: argparse.Namespace) -> None:
    """List models available on the Ollama server."""
    endpoint = args.endpoint
    try:
        all_models = fetch_local_models(endpoint)
    except Exception as exc:
        print(f"[ERROR] Cannot reach Ollama at {endpoint}: {exc}", file=sys.stderr)
        sys.exit(1)

    text_models = [m for m in all_models if m.get("family") not in VISION_FAMILIES]
    vision_models = [m for m in all_models if m.get("family") in VISION_FAMILIES]

    print(f"[discover] {len(all_models)} models found at {endpoint}")
    print(f"  Text models ({len(text_models)}):")
    for m in text_models:
        ps = m.get("parameter_size", "?")
        fam = m.get("family", "?")
        quant = m.get("quantization", "?")
        print(f"    {m['name']:30s}  {ps:>6s}  {fam:12s}  {quant}")

    if vision_models:
        print(f"\n  Vision models ({len(vision_models)}) — excluded from eval:")
        for m in vision_models:
            print(f"    {m['name']:30s}  {m.get('parameter_size','?'):>6s}  {m.get('family','?')}")

    # Auto-select preview
    names, picks = auto_select_models(text_models, desired=6)
    print(f"\n  Auto-select would pick: {names}")


# =========================================================================
# status — show progress across phases
# =========================================================================

def cmd_status(args: argparse.Namespace) -> None:
    """Show progress of all phases."""
    print("[STATUS]")
    for phase in ["phase0", "phase1", "phase2", "phase3"]:
        phase_dir = RESULTS_ROOT / phase
        if not phase_dir.exists():
            print(f"  {phase}: not started")
            continue

        # Check for key files
        manifest = phase_dir / "manifest.jsonl"
        summary = phase_dir / "summary.json"
        survivors = phase_dir / "survivors.json"
        top_configs = phase_dir / "top_configs.json"
        reversibility = phase_dir / "reversibility.json"

        n_runs = 0
        if manifest.exists():
            n_runs = sum(1 for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip())

        parts = [f"{n_runs} runs"]
        if summary.exists():
            parts.append("summary OK")
        if survivors.exists():
            data = json.loads(survivors.read_text(encoding="utf-8"))
            parts.append(f"survivors: {data.get('survivors', [])}")
        if top_configs.exists():
            data = json.loads(top_configs.read_text(encoding="utf-8"))
            parts.append(f"top_configs: {data.get('top_configs', [])}")
        if reversibility.exists():
            data = json.loads(reversibility.read_text(encoding="utf-8"))
            n_pass = sum(1 for r in data if r.get("passed"))
            parts.append(f"reversibility: {n_pass}/{len(data)} pass")

        print(f"  {phase}: {', '.join(parts)}")


# =========================================================================
# CLI
# =========================================================================

def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--endpoint", default="http://localhost:11434",
                        help="Ollama endpoint (default: http://localhost:11434)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="experiments.eval",
        description="TCF evaluation pipeline — phased ablation design",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # discover
    p = sub.add_parser("discover", help="List available Ollama models")
    _add_common_args(p)

    # phase0
    p = sub.add_parser("phase0", help="Phase 0: encode/decode reversibility gate")

    # phase1
    p = sub.add_parser("phase1", help="Phase 1: basic formats x all models")
    _add_common_args(p)
    p.add_argument("--models", nargs="+", default=["auto"],
                   help="Models to test (default: auto-discover)")
    p.add_argument("--desired-models", type=int, default=6,
                   help="Number of models for auto-discovery (default: 6)")
    p.add_argument("--survivor-threshold", type=float, default=0.3,
                   help="Minimum compute accuracy to pass to Phase 2 (default: 0.3)")
    p.add_argument("--top-survivors", type=int, default=5,
                   help="Minimum number of survivors (default: 5)")

    # phase2
    p = sub.add_parser("phase2", help="Phase 2: TCF encoding variants x survivors")
    _add_common_args(p)
    p.add_argument("--models", nargs="+", default=None,
                   help="Override models (default: load from phase1/survivors.json)")

    # phase3
    p = sub.add_parser("phase3", help="Phase 3: scaling + interactions with top configs")
    _add_common_args(p)

    # status
    p = sub.add_parser("status", help="Show progress of all phases")

    args = parser.parse_args()

    dispatch = {
        "discover": cmd_discover,
        "phase0": cmd_phase0,
        "phase1": cmd_phase1,
        "phase2": cmd_phase2,
        "phase3": cmd_phase3,
        "status": cmd_status,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
