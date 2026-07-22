"""T1 — o teste decisivo do posicionamento de transmissao (2026-07-05).

Pergunta (transmissao-api-onde-tcf-importa.md, 2026-06-21): toda a evidencia de
"TCF ganha" e' vs CSV+brotli. O concorrente TEXTUAL real e' NDJSON+brotli (padrao
BigQuery/Elasticsearch/X API). Enquanto nao medirmos TCF+brotli vs NDJSON+brotli,
a tese de transmissao fica em aberto. Este lab mede.

FORK exploratorio — NAO toca src/tcf. Datasets reais em Z:/tcf-data/external.

Fairness (pre-registrado; o workflow adversarial critica):
- Mesma data logica em TODOS os formatos: primeiras N linhas do CSV raw, TODAS as
  colunas (sem exclusao), valores como strings do CSV.
- CSV: csv.writer (quoting correto) — nao join naive (corromperia em virgulas).
- NDJSON-str: json por linha, valores STRING (fiel ao CSV, apples-to-apples c/ TCF).
- NDJSON-typed (STEELMAN): int/float sem aspas QUANDO bijetivo (str(x)==orig, guarda
  leading-zero/precisao) -> NDJSON o MENOR justo possivel (dificil de bater = honesto).
- JSON-array (teto): array unico de objetos typed.
- TCF: encode(table) v0.7 default. RT OBRIGATORIO: decode(tcf)==table senao FLAG.
- Compressores: brotli q11 (melhor de cada) + gzip-9 (controle). Mesmo q p/ todos.
- Sem sort_by (lever ortogonal, T-E/T2). Ordem natural.

Metrica decisiva por (dataset, scale): TCF+brotli vs {NDJSON-typed, NDJSON-str,
CSV, JSON-array}+brotli — bytes + % delta. Agregado weighted (soma de bytes).
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode          # noqa: E402
import brotli                            # noqa: E402

EXT = Path("Z:/tcf-data/external")

# 6 datasets reais cobrindo o espectro de favorabilidade (viés declarado):
#   favoravel (low-card categorico/estruturado): adult, ibge
#   misto (categorico + free-text/enderecos):    online-retail, receita
#   desfavoravel (high-card/free-text/numerico):  pessoas (CPF/nomes), lineitem (l_comment)
DATASETS = [
    ("adult",         EXT / "adult-census" / "adult.csv",        "favoravel"),
    ("ibge-munic",    EXT / "ibge-municipios" / "municipios.csv", "favoravel"),
    ("online-retail", EXT / "online-retail" / "online_retail.csv", "misto"),
    ("receita",       EXT / "receita-cnpj" / "estabelecimentos.csv", "misto"),
    ("pessoas",       EXT / "br-identidades" / "pessoas.csv",    "desfavoravel"),
    ("tpch-lineitem", EXT / "tpch-sf001" / "lineitem.csv",       "desfavoravel"),
]
SCALES = [1000, 3000, 5000, 10000]


def load(path: Path, limit: int) -> dict[str, list[str]]:
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open(encoding=enc, newline="") as f:
                r = csv.reader(f)
                header = next(r)
                cols: dict[str, list[str]] = {h: [] for h in header}
                took = 0
                for row in r:
                    if took >= limit:
                        break
                    if len(row) != len(header):
                        continue
                    for h, v in zip(header, row):
                        cols[h].append(v)
                    took += 1
            return cols
        except UnicodeDecodeError:
            continue
    return {}


def _typed(v: str):
    """int/float sem aspas SO' quando bijetivo (round-trip byte-fiel)."""
    if v == "":
        return v
    # int: sem leading zero (exceto "0"), str(int)==orig
    try:
        i = int(v)
        if str(i) == v:
            return i
    except ValueError:
        pass
    # float: repr bijetivo (raro; preserva "3.5" mas nao "3.50")
    try:
        f = float(v)
        if repr(f) == v:
            return f
    except ValueError:
        pass
    return v


def to_csv(table: dict[str, list[str]]) -> str:
    keys = list(table)
    n = len(table[keys[0]])
    import io
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(keys)
    for i in range(n):
        w.writerow([table[k][i] for k in keys])
    return buf.getvalue()


def to_ndjson_str(table: dict[str, list[str]]) -> str:
    keys = list(table)
    n = len(table[keys[0]])
    out = []
    for i in range(n):
        out.append(json.dumps({k: table[k][i] for k in keys}, ensure_ascii=False))
    return "\n".join(out) + "\n"


def to_ndjson_typed(table: dict[str, list[str]]) -> str:
    keys = list(table)
    n = len(table[keys[0]])
    out = []
    for i in range(n):
        out.append(json.dumps({k: _typed(table[k][i]) for k in keys}, ensure_ascii=False))
    return "\n".join(out) + "\n"


def to_json_array(table: dict[str, list[str]]) -> str:
    keys = list(table)
    n = len(table[keys[0]])
    arr = [{k: _typed(table[k][i]) for k in keys} for i in range(n)]
    return json.dumps(arr, ensure_ascii=False)


def to_json_columnar(table: dict[str, list[str]]) -> str:
    """STEELMAN JSON maximo: colunar {col:[values]} — chaves UMA vez (remove a
    repeticao de chaves por linha, a maior desvantagem do NDJSON e' exatamente
    onde o TCF ganha estrutura). Se TCF+brotli bater ISTO, a conclusao e' robusta."""
    keys = list(table)
    n = len(table[keys[0]])
    return json.dumps({k: [_typed(table[k][i]) for i in range(n)] for k in keys},
                      ensure_ascii=False)


def nbytes(s: str) -> int:
    return len(s.encode("utf-8"))


def gz(s: str) -> int:
    return len(gzip.compress(s.encode("utf-8"), 9))


def br(s: str, q: int = 11) -> int:
    return len(brotli.compress(s.encode("utf-8"), quality=q))


def rt_ok(table: dict[str, list[str]], tcf_text: str) -> bool:
    try:
        got = decode(tcf_text)
    except Exception:
        return False
    if not isinstance(got, dict):
        return False
    if list(got.keys()) != list(table.keys()):
        return False
    for k in table:
        if list(map(str, got[k])) != table[k]:
            return False
    return True


def main():
    results = []
    for label, path, favor in DATASETS:
        if not path.exists():
            print(f"== {label}: SKIP (sem dataset) ==", file=sys.stderr)
            continue
        for scale in SCALES:
            table = load(path, scale)
            if not table:
                continue
            n = len(next(iter(table.values())))
            if n < scale * 0.5:  # dataset menor que o scale pedido
                if n == 0:
                    continue
            ncol = len(table)

            reps = {
                "csv": to_csv(table),
                "ndjson_str": to_ndjson_str(table),
                "ndjson_typed": to_ndjson_typed(table),
                "json_array": to_json_array(table),
                "json_columnar": to_json_columnar(table),
            }
            t0 = time.perf_counter()
            tcf_text = encode(table)
            enc_ms = (time.perf_counter() - t0) * 1000
            reps["tcf"] = tcf_text
            rt = rt_ok(table, tcf_text)

            row = {
                "dataset": label, "favor": favor, "scale": n, "cols": ncol,
                "rt_ok": rt, "tcf_encode_ms": round(enc_ms, 1),
            }
            for name, s in reps.items():
                row[f"{name}_raw"] = nbytes(s)
                row[f"{name}_gz"] = gz(s)
                row[f"{name}_br"] = br(s)        # q11 (melhor de cada)
                row[f"{name}_br5"] = br(s, 5)     # q5 (HTTP dinamico realista)
            results.append(row)
            flag = "" if rt else "  [RT-FAIL]"
            print(f"{label:14s} n={n:6d} c={ncol:2d} | tcf+br={row['tcf_br']:7d} "
                  f"ndj-typed+br={row['ndjson_typed_br']:7d} "
                  f"json-col+br={row['json_columnar_br']:7d} "
                  f"csv+br={row['csv_br']:7d}{flag}", file=sys.stderr)

    out = Path(__file__).resolve().parent / "results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n[t1] {len(results)} medicoes -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
