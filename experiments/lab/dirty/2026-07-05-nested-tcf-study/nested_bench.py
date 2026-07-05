"""Nested-TCF study — como o TCF (tabular) trataria payloads JSON ANINHADOS (2026-07-05).

Owner pediu, antes de completar a matriz de transmissao: estudar como o TCF lida com o
envio padrao (JSON de request/response, as vezes multi-camada / instrucao aninhada), e se
da' pra ter um "TCF aninhado similar ao JSON". Este harness MEDE (nao especula).

Perfil DUPLO (ADR-nenhum; nota transmissao):
  - REQUEST (upload): config/instrucao multi-camada + array de itens (batch). Tipicamente pequeno.
  - RESPONSE (download): envelope aninhado + ARRAY GRANDE homogeneo (o volume; nicho do TCF).

Tese do estudo (a testar): JSON aninhado = ESQUELETO escalar (config, pequeno) + ARRAYS-DE-OBJETOS
(tabulares, onde vive o volume). TCF ja' e' a ferramenta nativa dos arrays-de-objetos (multi-col
dict). "TCF aninhado" = manter o esqueleto fino + hoistar cada array-de-objetos para um BLOCO TCF.

NB "nesting": o TCF ja' faz nesting em nivel de VALOR/afixo (HCC: filho_de(no=...)+"..."; ver
old/M0-.../2026-05-10-05-patricia-aninhado). Isto e' OUTRO nesting — de DOCUMENTO (arvore obj/array).

3 adaptadores nested<->TCF (LAB, nao toca src/tcf):
  A) flatten_dotted   — achata toda folha p/ (path, json_value) -> 1 tabela TCF 2-col. RT via unflatten.
  B) nested_tcf       — "TCF aninhado": esqueleto JSON fino c/ placeholders + 1 bloco TCF por array-de-objetos.
  C) (comparacao)     — raw JSON compacto e JSON-colunar (arrays -> {col:[...]}); steelmen ja' medidos no T1.

Deterministico (seed fixa, sem random/clock). Rotulos SINTETICOS/anonimizados (ASSET_SYN_*,
cumulative_metric) — a FORMA importa, nao os rotulos. Ecologico, vies TCF-favoravel declarado nos
arrays cadenciados.
"""
from __future__ import annotations
import json
import gzip
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode, SideOutputs   # noqa: E402
import brotli                                 # noqa: E402

SEP = "\x1e"  # record separator entre esqueleto e blocos TCF (nao aparece em texto normal)


# ---------------------------------------------------------------------------
# Payloads sinteticos (anonimizados, deterministicos)
# ---------------------------------------------------------------------------
def gen_forecast(n: int):
    """(ds, yhat) horario, drift de minuto + yhat cumulativo reset-diario. Deterministico.
    Espelha a forma da resposta /forecast (cumulate=true, reset=day). Copia do forecast_bench (T1)."""
    ds, yhat = [], []
    t = datetime(2026, 7, 4, 23, 37)
    acc = 0.0
    last_day = t.day
    for i in range(n):
        t = t + timedelta(hours=1)
        if i % 12 == 11:
            t = t + timedelta(minutes=1)
        if t.day != last_day:
            acc = 0.0
            last_day = t.day
        step = 60 + ((i * 37) % 15) - 7 + (i % 24) * 0.4
        acc += step
        ds.append(t.strftime("%Y-%m-%dT%H:%M"))
        yhat.append(round(acc, 4))
    return ds, yhat


def gen_request(n_assets: int) -> dict:
    """REQUEST (upload): instrucao multi-camada (options/window aninhados) + array de series (batch).
    Config escalar pequeno; o array 'series' cresce com n_assets (onde o TCF pode ajudar em batch)."""
    return {
        "model": "seasonal-cumulative",
        "options": {
            "cumulate": True, "reset": "day", "horizon": "1m",
            "freq": "H", "tz": "UTC", "fill_gaps": "interpolate",
        },
        "window": {"start": "2026-07-01T00:00", "end": "2026-07-31T23:00"},
        "series": [
            {"asset": f"ASSET_SYN_{i:04d}", "variable": "cumulative_metric",
             "unit": "unit_a", "weight": 1.0}
            for i in range(1, n_assets + 1)
        ],
    }


def gen_response(n_pts: int) -> dict:
    """RESPONSE (download): envelope aninhado (asset/variable/'-') + array GRANDE cadenciado 'forecast'."""
    ds, yhat = gen_forecast(n_pts)
    return {"ASSET_SYN_01": {"cumulative_metric": {"-": {
        "projectable": True,
        "messages": ["ok", "cumulative", "gap.variable"],
        "forecast": [{"ds": ds[i], "yhat": yhat[i]} for i in range(n_pts)],
    }}}}


# ---------------------------------------------------------------------------
# Baselines JSON (steelmen ja' usados no T1)
# ---------------------------------------------------------------------------
def raw_json(obj) -> str:
    """JSON compacto (separators minimos) — steelman de tamanho do JSON cru."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _columnarize(obj):
    """Recursivamente troca todo array-de-objetos homogeneo por {col:[...]} (JSON-colunar).
    Steelman JSON maximo: chaves uma vez. RT trivial (estrutura preservada, so' transposta)."""
    if isinstance(obj, dict):
        return {k: _columnarize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        if obj and all(isinstance(e, dict) for e in obj):
            cols = list(dict.fromkeys(k for e in obj for k in e))
            return {"__cols__": cols, **{c: [_columnarize(e.get(c)) for e in obj] for c in cols}}
        return [_columnarize(e) for e in obj]
    return obj


def json_columnar(obj) -> str:
    return json.dumps(_columnarize(obj), ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Adaptador A — flatten_dotted (toda folha -> (path, json_value)) -> TCF 2-col
# ---------------------------------------------------------------------------
def flatten_pairs(obj, prefix="", out=None):
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten_pairs(v, f"{prefix}.{k}" if prefix else k, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flatten_pairs(v, f"{prefix}.{i}", out)
    else:
        out.append((prefix, json.dumps(obj, ensure_ascii=False)))  # json_value self-describing (tipo)
    return out


def unflatten(pairs):
    """Reconstroi a arvore a partir de (path, json_value). Convencao: segmento so'-digitos = indice de array.
    Caveat (con): chaves com '.' ou vazias, arrays/objetos vazios, nao sobrevivem (nao ocorrem nas formas aqui)."""
    root = {}
    for path, jval in pairs:
        segs = path.split(".")
        cur = root
        for seg in segs[:-1]:
            cur = cur.setdefault(seg, {})
        cur[segs[-1]] = json.loads(jval)
    return _listify(root)


def _listify(x):
    if isinstance(x, dict):
        x = {k: _listify(v) for k, v in x.items()}
        if x and all(k.isdigit() for k in x):
            return [x[k] for k in sorted(x, key=int)]
        return x
    return x


def flatten_dotted_tcf(obj):
    pairs = flatten_pairs(obj)
    paths = [p for p, _ in pairs]
    vals = [v for _, v in pairs]
    text = encode({"path": paths, "value": vals})
    rt_ok = unflatten(list(zip(paths, decode(text)["value"]))) == obj if paths else True
    return text, rt_ok


# ---------------------------------------------------------------------------
# Adaptador B — nested_tcf ("TCF aninhado"): esqueleto fino + bloco TCF por array-de-objetos
# ---------------------------------------------------------------------------
def _coltype(vals):
    """Tipo JSON dominante de uma coluna (assume homogenea; caveat p/ null/mixed)."""
    v = next((x for x in vals if x is not None), None)
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "num"
    return "str"


def _cell(v):
    """Serializa uma celula p/ o corpo TCF em STRING NUA (dominio do TCF; melhor bytes)."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""          # caveat: null vs "" ambiguo (nao ocorre nas formas aqui)
    return str(v)


def _retype(s, t):
    if t == "bool":
        return s == "true"
    if t == "num":
        return int(s) if ("." not in s and "e" not in s and "E" not in s) else float(s)
    return s


def hoist(obj, blocks):
    """Substitui cada array-de-objetos por {'@tcf_block':k} e guarda (cols, types, table) em blocks."""
    if isinstance(obj, dict):
        return {k: hoist(v, blocks) for k, v in obj.items()}
    if isinstance(obj, list):
        if obj and all(isinstance(e, dict) for e in obj):
            cols = list(dict.fromkeys(k for e in obj for k in e))
            table = {c: [_cell(e.get(c)) for e in obj] for c in cols}
            types = {c: _coltype([e.get(c) for e in obj]) for c in cols}
            k = len(blocks)
            blocks.append((cols, types, table))
            return {"@tcf_block": k}
        return [hoist(e, blocks) for e in obj]  # array-de-escalares fica inline (pequeno)
    return obj


def nested_tcf(obj):
    """Serializa: <esqueleto_json> SEP #BLOCK k <col:type ...> SEP <tcf_text> SEP ... . RT reconstroi."""
    blocks = []
    skeleton = hoist(obj, blocks)
    parts = [json.dumps(skeleton, ensure_ascii=False, separators=(",", ":"))]
    for k, (cols, types, table) in enumerate(blocks):
        hdr = f"#BLOCK {k} " + " ".join(f"{c}:{types[c]}" for c in cols)
        parts.append(hdr + "\n" + encode(table))
    text = SEP.join(parts)
    return text, blocks


def nested_tcf_decode(text):
    parts = text.split(SEP)
    skeleton = json.loads(parts[0])
    blocks = []
    for chunk in parts[1:]:
        hdr, body = chunk.split("\n", 1)
        toks = hdr.split()  # ['#BLOCK','k','col:type',...]
        types = {}
        for ct in toks[2:]:
            c, t = ct.rsplit(":", 1)
            types[c] = t
        table = decode(body)
        rows = [{c: _retype(table[c][i], types[c]) for c in table} for i in range(len(next(iter(table.values()))))]
        blocks.append(rows)
    return _reinsert(skeleton, blocks)


def _reinsert(obj, blocks):
    if isinstance(obj, dict):
        if set(obj.keys()) == {"@tcf_block"}:
            return blocks[obj["@tcf_block"]]
        return {k: _reinsert(v, blocks) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_reinsert(e, blocks) for e in obj]
    return obj


# ---------------------------------------------------------------------------
# Medidas
# ---------------------------------------------------------------------------
def nbytes(s): return len(s.encode("utf-8"))
def gz(s): return len(gzip.compress(s.encode("utf-8"), 9))
def br(s, q=11): return len(brotli.compress(s.encode("utf-8"), quality=q))


def measure(label, obj):
    rj = raw_json(obj)
    jc = json_columnar(obj)
    ft, ft_rt = flatten_dotted_tcf(obj)
    nt, _blocks = nested_tcf(obj)
    nt_rt = nested_tcf_decode(nt) == obj
    reps = {"raw_json": rj, "json_col": jc, "flatten_tcf": ft, "nested_tcf": nt}
    row = {k: {"raw": nbytes(v), "gz": gz(v), "br": br(v)} for k, v in reps.items()}
    return row, {"flatten_tcf": ft_rt, "nested_tcf": nt_rt}, reps


def pct(a, b): return 100.0 * a / b if b else float("nan")


def report():
    print("=" * 108)
    print("NESTED-TCF STUDY — payloads JSON aninhados: raw JSON / JSON-colunar / flatten-TCF / nested-TCF (+brotli q11)")
    print("=" * 108)

    print("\n### REQUEST (upload) — instrucao multi-camada + array 'series' (batch) — sweep n_assets")
    print(f"{'n_assets':>8s} | {'rawJSON':>8s} {'jsonCol':>8s} {'flatTCF':>8s} {'nestTCF':>8s} "
          f"| {'nest%raw':>9s} {'nest%col':>9s} | RT(flat,nest)")
    for n in [3, 20, 100, 500]:
        obj = gen_request(n)
        row, rt, _ = measure("req", obj)
        b = {k: row[k]["br"] for k in row}
        print(f"{n:8d} | {b['raw_json']:8d} {b['json_col']:8d} {b['flatten_tcf']:8d} {b['nested_tcf']:8d} "
              f"| {pct(b['nested_tcf'], b['raw_json']):8.1f}% {pct(b['nested_tcf'], b['json_col']):8.1f}% "
              f"| {rt['flatten_tcf']},{rt['nested_tcf']}")

    print("\n### RESPONSE (download) — envelope aninhado + array GRANDE cadenciado 'forecast' — sweep n_pts")
    print(f"{'n_pts':>6s} | {'rawJSON':>8s} {'jsonCol':>8s} {'flatTCF':>8s} {'nestTCF':>8s} "
          f"| {'nest%raw':>9s} {'nest%col':>9s} | RT(flat,nest)")
    for n in [24, 168, 744]:
        obj = gen_response(n)
        row, rt, reps = measure("resp", obj)
        b = {k: row[k]["br"] for k in row}
        print(f"{n:6d} | {b['raw_json']:8d} {b['json_col']:8d} {b['flatten_tcf']:8d} {b['nested_tcf']:8d} "
              f"| {pct(b['nested_tcf'], b['raw_json']):8.1f}% {pct(b['nested_tcf'], b['json_col']):8.1f}% "
              f"| {rt['flatten_tcf']},{rt['nested_tcf']}")

    # ---- Amostras p/ inspecao (writeup) ----
    print("\n" + "=" * 108)
    print("AMOSTRA 1 — nested_tcf da RESPONSE (24 pts): esqueleto fino + BLOCO TCF (veja a cadencia do ds)")
    print("=" * 108)
    obj = gen_response(24)
    nt, blocks = nested_tcf(obj)
    parts = nt.split(SEP)
    print("--- esqueleto JSON (placeholders @tcf_block) ---")
    print(parts[0])
    print("\n--- bloco 0 (forecast) — header + TCF body (primeiros 500 chars) ---")
    print(parts[1][:500])

    print("\n" + "=" * 108)
    print("AMOSTRA 2 — nested_tcf da REQUEST (20 assets): esqueleto + bloco 'series'")
    print("=" * 108)
    obj = gen_request(20)
    nt, blocks = nested_tcf(obj)
    parts = nt.split(SEP)
    print("--- esqueleto JSON ---")
    print(parts[0])
    print("\n--- bloco 0 (series) — header + TCF body ---")
    print(parts[1])

    # Salva outputs visiveis (NAO gitignored: .tcf.txt)
    out = HERE / "sample_nested_tcf.tcf.txt"
    obj744 = gen_response(744)
    nt744, _ = nested_tcf(obj744)
    out.write_text(nt744, encoding="utf-8")
    print(f"\n[salvo] {out.name} — nested_tcf da response 744pts ({nbytes(nt744)}B raw, {br(nt744)}B br)")


if __name__ == "__main__":
    report()
