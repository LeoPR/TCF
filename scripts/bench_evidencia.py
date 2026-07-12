"""Runner do material comprobatório 0.8 (T-QA-8 F1) — bytes + tempo + memória + RT.

FORA de src/tcf (regra §2.6 do ticket). Conceitos de telemetria portáveis em
[bench_evidencia_probes.py](bench_evidencia_probes.py) (F0-3: sondas isoladas,
fallback gracioso). stdlib-only.

Regras que este runner IMPÕE (T-QA-8 §2):
- RT SEMPRE: nenhum byte reportado sem `decode(encode(x)) == x` na mesma run;
  RT quebrado -> registro de ERRO sem bytes/tempo (nunca número órfão).
- Medir, não calcular: todo campo sai de execução.
- Régua: `--validate-pins` confere o runner contra os 3 pinos da suíte
  (D1-D9=1523B, D17a=300B, real-world=89616B) — divergiu, é bug DO RUNNER
  (F1-4): não produza material.

Uso:
    python scripts/bench_evidencia.py --validate-pins
    python scripts/bench_evidencia.py --dataset datasets/synthetic/D17a-multi-column-mixed.csv \
        --fase f2 --out experiments/results/evidencia-0.8
    python scripts/bench_evidencia.py --dataset D1-emails-simples --fase f2 \
        --kwargs '{"sort_by": null}' --n 9 --warmup 2

Como biblioteca (o caminho principal nas fases F2-F4):
    from bench_evidencia import run_case, load_csv_auto, write_jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from bench_evidencia_probes import (  # noqa: E402
    env_fingerprint, measure_repeat, peak_heap_bytes, peak_rss_bytes,
)
from tcf import decode, encode  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402

SCHEMA_ID = "evidencia-0.8/v1"
RESULTS_DIR = ROOT / "experiments" / "results" / "evidencia-0.8"

# --- Pinos da régua (F1-4). FONTE = a suíte (tests/test_regression_v1_baseline.py
# + tests/test_real_world_snapshots.py); duplicado AQUI só pra validação cruzada
# do runner — em divergência, O TESTE MANDA (princípio: a prosa aponta, o teste mede).
PIN_D1_D9_TOTAL = 1523
PIN_D17A = 300
PIN_REAL_WORLD_TOTAL = 89616
_D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]
_REAL_WORLD = [
    "online-retail/description-2k.csv",
    "online-retail/stockcode-2k.csv",
    "tpch-sf001/lcomment-2k.csv",
]


# ---------------------------------------------------------------------------
# Carga de datasets — MESMA carga da régua (cópia documentada dos loaders da
# suíte; mudar aqui sem mudar lá quebra o --validate-pins de propósito)
# ---------------------------------------------------------------------------

def load_csv_single(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r)                                    # header
        return [row[0] for row in r if row]


def load_csv_multi(path: Path) -> dict[str, list[str]]:
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        cols: dict[str, list[str]] = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def load_csv_auto(path: Path):
    """1 coluna no header -> list (single-col); 2+ -> dict (multi-col)."""
    with path.open(encoding="utf-8", newline="") as f:
        header = next(csv.reader(f))
    return load_csv_single(path) if len(header) == 1 else load_csv_multi(path)


# ---------------------------------------------------------------------------
# Serialização de SideOutputs (F1-2) — externo ao dataclass, por design
# ---------------------------------------------------------------------------

def serialize_side(side: SideOutputs, include_traces: bool = False) -> dict:
    """SideOutputs -> dict JSON-serializável. Compacto por default (traces do
    OBAT/HCC são grandes; opt-in via include_traces)."""
    out: dict = {}
    if side.multi_info is not None:
        out["multi_info"] = side.multi_info
    if side.per_col:
        cols = {}
        for name, pc in side.per_col.items():
            cols[name] = {
                "body_bytes": pc.body_bytes,           # candidato tcf (custo compute)
                "emitted_bytes": pc.emitted_bytes,     # emitido no body (BUG-07)
                "emitted_mode": pc.emitted_mode,
                "min_len": pc.min_len,
                "cadence_detected": pc.cadence_detected,
                "obat_used_hint": pc.obat_used_hint,
                "seq_rle_runs": len(pc.seq_rle_runs or []),
            }
            if include_traces:
                cols[name]["obat_log"] = pc.obat_log
                cols[name]["hcc_trace"] = pc.hcc_trace
        out["per_col"] = cols
    if side.nature_apply is not None:
        out["nature_apply"] = side.nature_apply
    for f in ("min_len", "cadence_detected", "body_bytes"):   # single-col
        v = getattr(side, f)
        if v is not None:
            out.setdefault("single", {})[f] = v
    return out


# ---------------------------------------------------------------------------
# O caso de medição
# ---------------------------------------------------------------------------

def _input_bytes(data) -> int:
    """Baseline de comparação: bytes UTF-8 dos valores unidos por LF
    (por coluna, somado) — o 'raw' contra o qual o blob é medido."""
    if isinstance(data, dict):
        return sum(len("\n".join(vals).encode("utf-8")) for vals in data.values())
    return len("\n".join(data).encode("utf-8"))


def run_case(dataset_id: str, data, encode_kwargs: dict | None = None, *,
             n: int = 9, warmup: int = 2, source: str | None = None,
             seed: int | None = None, include_traces: bool = False) -> dict:
    """Mede UM caso (dataset × kwargs) e retorna o registro JSONL.

    Ordem do protocolo: RT primeiro (sem RT válido, sem bytes); determinismo;
    tempos (encode E decode, mediana de n com warmup); memória em runs
    SEPARADAS (heap com sonda tem overhead — não contamina o tempo)."""
    kw = dict(encode_kwargs or {})
    base = {
        "schema": SCHEMA_ID,
        "dataset": {
            "id": dataset_id,
            "source": source,
            "n_rows": (len(next(iter(data.values()))) if isinstance(data, dict)
                       else len(data)),
            "n_cols": len(data) if isinstance(data, dict) else 1,
            "kind": "multi" if isinstance(data, dict) else "single",
        },
        "encode_kwargs": kw,
        "seed": seed,
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "env": env_fingerprint(),
    }

    # 1) RT obrigatório (regra §2.1) — falhou: registro de erro SEM números.
    # Contrato de entrada do runner: valores JÁ como str (carga via load_csv_*).
    side = SideOutputs()
    blob = encode(data, side_outputs=side, **kw)
    decoded = decode(blob)
    sort_t = bool(kw.get("sort_by"))
    anon_t = bool(kw.get("drop_names")) or (isinstance(data, dict) and "" in data)
    if sort_t or anon_t:
        # Transformação DECLARADA: identidade não vale por design. O cheque tem
        # DUAS pernas (achado da verificação adversarial F1 — idempotência
        # sozinha aceitaria um decode-constante):
        # (a) CONTEÚDO preservado sob a transformação —
        #     sort_by: multiset de LINHAS igual (reordenação não cria/perde linha);
        #     anônimas: VALORES por coluna, na ordem, iguais (só as chaves mudam);
        # (b) IDEMPOTÊNCIA na 2ª geração: dado transformado é ponto-fixo do RT.
        if isinstance(data, dict) and isinstance(decoded, dict):
            if sort_t:
                rows_in = sorted(zip(*data.values()))
                rows_out = sorted(zip(*decoded.values()))
                content_ok = (rows_in == rows_out
                              and (anon_t or list(decoded) == list(data)))
            else:
                content_ok = list(decoded.values()) == list(data.values())
        else:
            content_ok = False
        rt_ok = content_ok and decode(encode(decoded, **kw)) == decoded
        base["rt_mode"] = "conteudo-sob-transformacao + idempotencia-2a-geracao"
    else:
        rt_ok = decoded == data
        base["rt_mode"] = "identidade"
    if not rt_ok:
        return {**base, "rt_ok": False,
                "error": "RT quebrado — bytes NAO reportados (T-QA-8 §2.1)"}

    # 2) determinismo byte-a-byte (mesmo processo)
    deterministic = encode(data, **kw) == blob

    # 3) bytes — medidos do próprio artefato. Header = linha do magic (+LF) em
    # QUALQUER forma com magic: '#TCF.8M' (multi), '#TCF.8 ' (single+spec),
    # '#TCF.8\n' (version-stamp). Órfão = 0 (o encoder auto-escapa dado que
    # pareceria magic, então startswith é seguro aqui).
    raw = blob.encode("utf-8")
    nl1 = raw.find(b"\n")
    has_magic = blob.startswith("#TCF.8")
    rec_bytes = {
        "total": len(raw),
        "header": (nl1 + 1) if has_magic else 0,
        "body": len(raw) - (nl1 + 1) if has_magic else len(raw),
        "input_join_lf": _input_bytes(data),
    }

    # 4) tempo (mediana de n, warmup; encode e decode separados)
    timing = {
        "encode": measure_repeat(lambda: encode(data, **kw), n=n, warmup=warmup),
        "decode": measure_repeat(lambda: decode(blob), n=n, warmup=warmup),
    }

    # 5) memória (runs separadas; campos ausentes = sonda indisponível)
    _, enc_heap = peak_heap_bytes(lambda: encode(data, **kw))
    _, dec_heap = peak_heap_bytes(lambda: decode(blob))
    memory = {}
    if enc_heap is not None:
        memory["encode_peak_heap_bytes"] = enc_heap
    if dec_heap is not None:
        memory["decode_peak_heap_bytes"] = dec_heap
    rss = peak_rss_bytes()
    if rss is not None:
        memory["process_peak_rss_bytes"] = rss

    return {**base, "rt_ok": True, "deterministic": deterministic,
            "bytes": rec_bytes, "timing": timing, "memory": memory,
            "side": serialize_side(side, include_traces=include_traces)}


def _json_safe(obj):
    """Sanitiza pro JSONL: objetos não-JSON (ex.: spec de nature em
    encode_kwargs/nature_apply) viram seu `name` (id portável) ou repr."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return getattr(obj, "name", None) or repr(obj)


def write_jsonl(records, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(_json_safe(rec), ensure_ascii=False) + "\n")
    return out_path


# ---------------------------------------------------------------------------
# F1-4 — validação do runner contra a régua (os pinos da suíte)
# ---------------------------------------------------------------------------

def validate_pins(verbose: bool = True) -> bool:
    """Runner DEVE medir o que os testes medem. Divergiu -> bug do runner, PARE."""
    ok = True
    lines = []

    total = 0
    for name in _D1_D9:
        values = load_csv_single(ROOT / "datasets" / "synthetic" / f"{name}.csv")
        rec = run_case(name, values, n=1, warmup=0)
        assert rec["rt_ok"], f"RT quebrado em {name}"
        total += rec["bytes"]["total"]
    ok &= total == PIN_D1_D9_TOTAL
    lines.append(f"D1-D9 total: {total}B (pino {PIN_D1_D9_TOTAL}) "
                 f"{'OK' if total == PIN_D1_D9_TOTAL else 'DIVERGIU'}")

    cols = load_csv_multi(ROOT / "datasets" / "synthetic" / "D17a-multi-column-mixed.csv")
    rec = run_case("D17a", cols, n=1, warmup=0)
    ok &= rec["rt_ok"] and rec["bytes"]["total"] == PIN_D17A
    lines.append(f"D17a: {rec['bytes']['total']}B (pino {PIN_D17A}) "
                 f"{'OK' if rec['bytes']['total'] == PIN_D17A else 'DIVERGIU'}")

    rw_total = 0
    for rel in _REAL_WORLD:
        path = ROOT / "datasets" / "samples" / rel
        values = load_csv_single(path)
        rec = run_case(rel, values, n=1, warmup=0,
                       source=path.relative_to(ROOT).as_posix())
        assert rec["rt_ok"], f"RT quebrado em {rel}"
        rw_total += rec["bytes"]["total"]
    ok &= rw_total == PIN_REAL_WORLD_TOTAL
    lines.append(f"real-world total: {rw_total}B (pino {PIN_REAL_WORLD_TOTAL}) "
                 f"{'OK' if rw_total == PIN_REAL_WORLD_TOTAL else 'DIVERGIU'}")

    if verbose:
        print("\n".join(lines))
        print("VALIDACAO:", "OK — runner mede o que a suite mede"
              if ok else "FALHOU — bug do RUNNER; nao produza material")
    return bool(ok)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--validate-pins", action="store_true",
                    help="confere o runner contra os 3 pinos da suite (F1-4)")
    ap.add_argument("--dataset", help="caminho .csv OU nome em datasets/synthetic/")
    ap.add_argument("--fase", default="adhoc", help="subpasta do resultado (f2/f3/f4)")
    ap.add_argument("--out", default=str(RESULTS_DIR), help="dir base dos JSONL")
    ap.add_argument("--kwargs", default="{}", help="encode kwargs em JSON")
    ap.add_argument("--n", type=int, default=9)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--save-blob", action="store_true",
                    help="salva o .tcf de exemplo ao lado do JSONL (inspecao)")
    args = ap.parse_args(argv)

    if args.validate_pins:
        return 0 if validate_pins() else 1

    if not args.dataset:
        ap.error("--dataset obrigatorio (ou use --validate-pins)")
    path = Path(args.dataset)
    if not path.exists():
        path = ROOT / "datasets" / "synthetic" / f"{args.dataset}.csv"
    if not path.exists():
        ap.error(f"dataset nao encontrado: {args.dataset}")

    data = load_csv_auto(path)
    kw = json.loads(args.kwargs)
    src = (path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
    rec = run_case(path.stem, data, kw, n=args.n, warmup=args.warmup,
                   source=src.as_posix())     # forward-slash: registro portavel
    out = write_jsonl([rec], Path(args.out) / args.fase / f"{path.stem}.jsonl")
    print(f"registro -> {out}")
    if args.save_blob and rec.get("rt_ok"):
        blob_path = out.with_suffix(".tcf")
        blob_path.write_text(encode(data, **kw), encoding="utf-8", newline="\n")
        print(f"blob     -> {blob_path}")
    if not rec.get("rt_ok"):
        print("ERRO: RT quebrado — bytes nao reportados.")
        return 2
    print(f"bytes={rec['bytes']['total']} rt=OK det={rec['deterministic']} "
          f"enc_median={rec['timing']['encode']['median_ns'] / 1e6:.2f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
