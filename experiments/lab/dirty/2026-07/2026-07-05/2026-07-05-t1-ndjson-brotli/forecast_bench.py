"""T1-download — o perfil DOWNLOAD (resposta de API), caso forecast (2026-07-05).

Perfil DUPLO das APIs: upload (request, foco economia de envio, tipicamente pequeno) vs
download (response, onde esta' o VOLUME). Forma tipica de um endpoint de forecast de serie
temporal: request pequeno (~250B, TCF nao ajuda), response = array grande de
{"ds": <timestamp horario cadenciado>, "yhat": <float>} (horizon 1m => ~744 pontos).

Essa resposta e' EXATAMENTE onde o TCF bate ate' o steelman JSON-colunar: `ds` e' cadenciado
(TCF modela via seq-RLE/delta), e NENHUM layout JSON captura a cadencia (escreve os 744
timestamps por extenso e deixa pro brotli). Aqui medimos isso.

Modelado numa forma GENERICA de resposta de forecast (rotulos SINTETICOS/anonimizados; a
FORMA — nested + array cadenciado — e' o que importa, nao os rotulos). ECOLOGICO, nao stress.
VIES DECLARADO: TCF-favoravel por construcao (ds cadenciado). Nao e' evidencia primaria — e'
ilustracao do perfil download.

FORK — nao toca src/tcf. Deterministico (seed fixa, sem random/clock).
"""
from __future__ import annotations
import json
import gzip
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode          # noqa: E402
import brotli                            # noqa: E402


def gen_forecast(n: int):
    """Gera (ds, yhat) horario com drift de minuto + yhat cumulativo reset-diario.
    Deterministico. Espelha a forma da resposta /forecast (cumulate=true, reset=day)."""
    ds, yhat = [], []
    t = datetime(2026, 7, 4, 23, 37)
    acc = 0.0
    last_day = t.day
    for i in range(n):
        # drift de minuto: a cada ~12 passos o minuto anda +1 (como no exemplo real :37->:38)
        t = t + timedelta(hours=1)
        if i % 12 == 11:
            t = t + timedelta(minutes=1)
        if t.day != last_day:
            acc = 0.0            # reset diario (cumulate/reset=day)
            last_day = t.day
        # incremento horario ~55-70 com curva suave (deterministico via seno inteiro)
        step = 60 + ((i * 37) % 15) - 7 + (i % 24) * 0.4
        acc += step
        ds.append(t.strftime("%Y-%m-%dT%H:%M"))
        yhat.append(round(acc, 4))
    return ds, yhat


def envelope_json(ds, yhat) -> str:
    """Forma tipica de resposta forecast (nested + array de objetos). Rotulos SINTETICOS
    (asset/metric anonimizados) — so' a estrutura importa pro tamanho."""
    resp = {"ASSET_SYN_01": {"cumulative_metric": {"-": {
        "projectable": True,
        "messages": ["ok", "cumulative", "gap.variable"],
        "forecast": [{"ds": ds[i], "yhat": yhat[i]} for i in range(len(ds))],
    }}}}
    return json.dumps(resp, ensure_ascii=False)


def ndjson_rows(ds, yhat) -> str:
    return "\n".join(json.dumps({"ds": ds[i], "yhat": yhat[i]}, ensure_ascii=False)
                     for i in range(len(ds))) + "\n"


def columnar_json(ds, yhat) -> str:
    return json.dumps({"ds": ds, "yhat": yhat}, ensure_ascii=False)


def nbytes(s): return len(s.encode("utf-8"))
def gz(s): return len(gzip.compress(s.encode("utf-8"), 9))
def br(s, q=11): return len(brotli.compress(s.encode("utf-8"), quality=q))


HORIZONS = [("1d", 24), ("1w", 168), ("1m", 744)]

print("=" * 96)
print("T1-download — resposta /forecast (ds cadenciado + yhat) — +brotli q11")
print("=" * 96)
print(f"{'horizon':8s} {'pts':>4s} | {'envJSON':>8s} {'ndjson':>8s} {'jsonCol':>8s} {'tcf':>8s} "
      f"| {'tcf%envJSON':>11s} {'tcf%jsonCol':>11s} RT")
for name, n in HORIZONS:
    ds, yhat = gen_forecast(n)
    table = {"ds": ds, "yhat": [str(y) for y in yhat]}  # TCF: strings (fiel)
    tcf_text = encode(table)
    # RT
    try:
        g = decode(tcf_text)
        rt = isinstance(g, dict) and all(list(map(str, g[k])) == table[k] for k in table)
    except Exception:
        rt = False
    reps = {
        "env": envelope_json(ds, yhat),
        "ndjson": ndjson_rows(ds, yhat),
        "jsoncol": columnar_json(ds, yhat),
        "tcf": tcf_text,
    }
    b = {k: br(v) for k, v in reps.items()}
    p_env = 100.0 * b["tcf"] / b["env"]
    p_col = 100.0 * b["tcf"] / b["jsoncol"]
    print(f"{name:8s} {n:4d} | {b['env']:8d} {b['ndjson']:8d} {b['jsoncol']:8d} {b['tcf']:8d} "
          f"| {p_env:10.1f}% {p_col:10.1f}% {'ok' if rt else 'FAIL'}")

# amostra do TCF pra inspecao (mostra a cadencia capturada)
ds, yhat = gen_forecast(24)
t = encode({"ds": ds, "yhat": [str(y) for y in yhat]})
print("\n--- amostra TCF (24 pts) — veja se a cadencia de ds vira seq-RLE ---")
print(t[:400])
