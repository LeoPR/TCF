"""Runner do baseline — o PROCESSO cristalizado (schema perf-baseline-09/v1).

Le a matriz congelada (cases.json), constroi cada caso de forma DETERMINISTICA,
roda os gates de classe ANTES do cronometro, mede encode/decode/prepare/verify
com amostras cruas (wall+cpu), intercala a sentinela a cada N casos e carimba o
sha do manifesto em cada registro. O .9 roda ISTO de novo e o compare.py junta
por case_id.

Disciplina herdada do harness de bytes: (1) RT e' gate — sem RT nao ha' numero;
(2) classe fora do alcance (G2) => celula rejeitada, nunca cobrada do TCF;
(3) um caso que estoura NAO derruba a rodada (licao do F3) — vira registro de
erro e segue. Vetor nao-implementado ainda => status "pendente" com motivo,
JAMAIS numero fingido.

    python -m bench_perf.runner --smoke        # dry-run: toda celula em n=100
    python -m bench_perf.runner                # baseline completo
    python -m bench_perf.runner --only B1,B2   # so' alguns blocos
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from bench_perf import probes as P                              # noqa: E402
from bench_perf import pivot as V                                # noqa: E402
from bench_perf import synth as SY                               # noqa: E402
from bench_perf import calibrators as CAL                        # noqa: E402
from bench_perf import manifest as MAN                           # noqa: E402
from bench_perf import crosscompat as CC                         # noqa: E402

SAIDA = REPO / "experiments" / "results" / "perf-baseline"
SENTINELA_CADA = 10


# ----------------------------------------------------------------- construcao do dado

def _escala(case: dict, smoke: bool) -> dict:
    e = dict(case["vectors"]["escala"])
    if smoke:
        e["R"] = min(e.get("R", 100), 100)      # dry-run: tudo minusculo
    return e


def build_pivot(case: dict, smoke: bool) -> V.Pivot:
    """Constroi o pivo do caso. synth e' o unico caminho hoje; real/pins ficam
    pendentes (declarado, nao fingido)."""
    fonte = case["fonte"]
    e = _escala(case, smoke)
    forma = case["vectors"]["forma"]
    if fonte == "synth":
        return SY.synth_pivot(e.get("R", 100), e.get("C", 4), e.get("L", 32),
                              e.get("K", 0.1), forma, seed=SEED)
    raise _Pendente(f"fonte '{fonte}' ainda nao suportada pelo runner")


class _Pendente(Exception):
    """Vetor/fonte reconhecido mas nao implementado — status pendente, nao erro."""


def build_nested(case: dict, smoke: bool):
    """Records ANINHADOS a partir de um pivo flat, exercitando os caminhos do .8H.
    Dados-string (portaveis por construcao). O gate real do .8H e' o RT identidade."""
    fonte = case["fonte"]
    if fonte != "synth":
        raise _Pendente(f"fonte '{fonte}' ainda nao suportada")
    e = _escala(case, smoke)
    forma = case["vectors"]["forma"]
    C = max(2, e.get("C", 4))
    piv = SY.synth_pivot(e.get("R", 100), C, e.get("L", 32), e.get("K", 0.1),
                         "flat-mixed", seed=SEED)
    recs = V.to_records(piv)
    cols = list(piv.keys())
    if forma == "flat-mixed":                          # nao-regressao do .8H sobre dado PLANO
        return recs
    if forma == "nested-object":                       # metade das colunas -> sub-objeto
        meta = cols[: len(cols) // 2] or cols[:1]
        resto = [c for c in cols if c not in meta]
        return [{**{c: r[c] for c in resto}, "grupo": {c: r[c] for c in meta}} for r in recs]
    if forma == "nested-array":                        # agrupa linhas pela 1a coluna (K = fan-out)
        return V.nest_array_by_key(recs, cols[0])
    if forma == "nested-optional":                     # ~30% omitem a ultima coluna (mask P1)
        import random
        rng = random.Random(SEED)
        last = cols[-1]
        return [{k: v for k, v in r.items() if not (k == last and rng.random() < 0.3)}
                for r in recs]
    raise _Pendente(f"forma aninhada '{forma}' nao suportada")


def build_typed(case: dict, smoke: bool):
    """Records TIPADOS (int/float/bool/str), valores I-JSON-safe (dentro da classe
    N1). Isola o custo de TIPAR (do dado, nao do TCF). Aqui a cross-compat mais
    pega — o gate flag'aria int>2^53, mas o synth fica limpo de proposito."""
    import random
    e = _escala(case, smoke)
    n = e.get("R", 100)
    rng = random.Random(SEED ^ 0x7A17ED)
    recs = []
    for i in range(n):
        recs.append({
            "id": i,                                    # int (I-JSON-safe)
            "valor": round(rng.uniform(0, 1_000_000), 4),   # float finito
            "ativo": (i % 3 == 0),                      # bool
            "rotulo": f"item-{i % max(1, int(n * e.get('K', 0.1)))}",  # str
        })
    return recs


# ----------------------------------------------------------------- caminhos
# Cada caminho: (nome, prepara(pivot)->obj, serial(obj)->wire, desserial(wire)->obj).
# O RT verifica desserial(serial(prepara)) == prepara.

def _tcf_flat(pivot):
    from tcf import encode, decode
    return pivot, lambda p: encode(p), lambda w: decode(w)


def _json_ref_str(pivot):
    recs = V.to_records(pivot)
    V.g2_classe_json(recs)                                       # gate: prova de classe
    return recs, V.to_json_text, V.from_json_text


def _csv_ref(pivot):
    recs = V.to_records(pivot)
    if V.g3_classe_csv(recs) is None:
        raise V.ClasseRejeitada("G3", "csv nao round-trip (aspas/virgula/nl)")
    return recs, V.to_csv_text, V.from_csv_text


def _repr_null(pivot):
    # piso absoluto de I/O de string: junta por LF e separa. Por coluna.
    def ser(p):
        return "\x1e".join("\n".join(col) for col in p.values())

    nomes = list(pivot.keys())

    def des(w):
        partes = w.split("\x1e")
        return {nomes[i]: partes[i].split("\n") for i in range(len(nomes))}

    return pivot, ser, des


CAMINHOS = {
    "tcf-flat": _tcf_flat,
    "json-ref-str": _json_ref_str,
    "csv-ref": _csv_ref,
    "repr-null": _repr_null,
}

CAMINHOS_PENDENTES: set[str] = set()   # tcf-8h/nested/typed cobertos; B4 concorrencia via vetor


# ----------------------------------------------------------------- medicao de 1 caso

def run_case(case: dict, order_index: int, smoke: bool) -> dict:
    cid = case["case_id"]
    vet = case["vectors"]
    rec: dict = {
        "case_id": cid, "blocos": case.get("blocos", []), "order_index": order_index,
        "vectors": vet, "fonte": case["fonte"],
    }

    cam = vet["caminho"]

    # .8H / json aninhado: dados aninhados (builder proprio). Handler paralelo ao
    # caminho plano. json-ref-typed fica pendente (precisa de synth tipado).
    if cam in ("tcf-8h", "json-ref-nested", "json-ref-typed"):
        if vet["granularidade"] != "call" or vet["compressao"] != "none" \
                or vet["concorrencia"]["internal"] != "serial":
            rec["status"] = "pendente"
            rec["motivo"] = "vetor extra pendente no caminho aninhado"
            return rec
        try:
            data = build_typed(case, smoke) if cam == "json-ref-typed" else build_nested(case, smoke)
            V.g2_classe_json(data)                     # a jsonlib round-trip'a? (N1)
            rec["crosscompat"] = CC.resumo(CC.alertas(data))
            if cam == "tcf-8h":
                from tcf.hierarchical import encode_hierarchical, decode_hierarchical
                ser, des = encode_hierarchical, decode_hierarchical
            else:
                ser, des = V.to_json_text, V.from_json_text
            wire = ser(data)
            rec["rt_ok"] = des(wire) == data           # G5: RT identidade do .8H
            rec["bytes"] = len(wire.encode("utf-8"))
            if not rec["rt_ok"]:
                rec["status"] = "rt-quebrado"
                rec["motivo"] = "decode(encode(data)) != data"
                return rec
            rec["encode"] = P.medir(lambda: ser(data))
            rec["decode"] = P.medir(lambda: des(wire))
            rec["status"] = "ok"
            return rec
        except V.ClasseRejeitada as ex:
            rec["status"] = "rejeitado"; rec["gate"], rec["motivo"] = ex.gate, ex.motivo
            return rec
        except _Pendente as ex:
            rec["status"] = "pendente"; rec["motivo"] = str(ex)
            return rec
        except Exception as ex:
            rec["status"] = "erro"; rec["motivo"] = f"{type(ex).__name__}: {str(ex)[:200]}"
            return rec

    if cam in CAMINHOS_PENDENTES:
        rec["status"] = "pendente"
        rec["motivo"] = f"caminho '{cam}' ainda nao implementado no runner"
        return rec
    if cam not in CAMINHOS:
        rec["status"] = "pendente"
        rec["motivo"] = f"caminho '{cam}' desconhecido"
        return rec
    if vet["granularidade"] in ("candidate", "column", "process-tree"):
        rec["status"] = "pendente"
        rec["motivo"] = f"granularidade '{vet['granularidade']}' pendente"
        return rec
    if vet["concorrencia"]["internal"] != "serial" \
            or vet["concorrencia"]["test"] != "t1" or vet["accel"] != "cython":
        rec["status"] = "pendente"
        rec["motivo"] = "vetor concorrencia/accel pendente no runner"
        return rec

    # LAYER (B3): perfil por camada do encode tcf-flat, FORA do src/tcf (layers.py),
    # com gate de bytes identicos. So' faz sentido no caminho plano.
    if vet["granularidade"] == "layer":
        if cam != "tcf-flat":
            rec["status"] = "pendente"
            rec["motivo"] = "granularidade 'layer' so' no caminho tcf-flat"
            return rec
        try:
            from bench_perf import layers as LY
            from tcf import encode, decode
            pivot = build_pivot(case, smoke)
            V.g1_retangular(pivot)
            blob, camadas = LY.perfil_de(lambda: encode(pivot))
            rec["rt_ok"] = decode(blob) == pivot
            rec["bytes"] = len(blob.encode("utf-8"))
            rec["workload"] = SY.descrever(pivot)
            rec["layers"] = {k: v for k, v in camadas.items() if not k.startswith("_")}
            rec["layers_total_ns"] = camadas.get("_total_camadas_ns")
            rec["encode"] = P.medir(lambda: encode(pivot))     # o tempo agregado do tier
            rec["status"] = "ok" if rec["rt_ok"] else "rt-quebrado"
            return rec
        except Exception as e:
            rec["status"] = "erro"
            rec["motivo"] = f"{type(e).__name__}: {str(e)[:200]}"
            return rec

    try:
        # PREPARE medido (montar o dado que o caminho consome — hoje fora do cronometro
        # no harness antigo; aqui e' fronteira propria)
        t0 = P.time.perf_counter_ns()
        pivot = build_pivot(case, smoke)
        V.g1_retangular(pivot)
        obj, ser, des = CAMINHOS[cam](pivot)
        rec["prepare_ns"] = P.time.perf_counter_ns() - t0

        if cam.startswith("json") or cam.startswith("tcf"):     # alertas cross-compat -> metadado
            rec["crosscompat"] = CC.resumo(CC.alertas(obj if isinstance(obj, list) else V.to_records(obj)))
        wire = ser(obj)                                         # 1x pra pegar bytes + RT
        back = des(wire)
        rt_ok = back == obj
        rec["rt_ok"] = rt_ok
        rec["bytes"] = len(wire.encode("utf-8")) if isinstance(wire, str) else len(wire)
        rec["workload"] = SY.descrever(pivot)
        if not rt_ok:                                          # nenhum numero orfao
            rec["status"] = "rt-quebrado"
            rec["motivo"] = "desserial(serial(x)) != x"
            return rec

        rec["encode"] = P.medir(lambda: ser(obj))
        rec["decode"] = P.medir(lambda: des(wire))

        # COMPRESSAO (B6): cadeia total. O MESMO codec/nivel sobre este caminho.
        # serialize+compress vs decompress+parse — o que o mundo compara com o TCF.
        if vet["compressao"] != "none":
            from bench_perf import compress as CP
            try:
                comp, decomp = CP.get(vet["compressao"])
            except ImportError as e:
                rec["status"] = "pendente"
                rec["motivo"] = f"compressor ausente no ambiente: {e}"
                return rec
            wb = wire.encode("utf-8") if isinstance(wire, str) else wire
            packed = comp(wb)
            if decomp(packed) != wb:                          # RT do proprio codec
                rec["status"] = "erro"
                rec["motivo"] = "codec nao round-trip"
                return rec
            rec["chain"] = {
                "codec": vet["compressao"],
                "bytes_pre": len(wb), "bytes_post": len(packed),
                "ratio": round(len(packed) / len(wb), 4) if wb else None,
                "compress": P.medir(lambda: comp(wb)),
                "decompress": P.medir(lambda: decomp(packed)),
            }
        rec["status"] = "ok"
        return rec
    except V.ClasseRejeitada as e:
        rec["status"] = "rejeitado"
        rec["gate"], rec["motivo"] = e.gate, e.motivo           # fora da classe, nao e' erro do TCF
        return rec
    except _Pendente as e:
        rec["status"] = "pendente"
        rec["motivo"] = str(e)
        return rec
    except Exception as e:                                     # estouro NAO derruba a rodada
        rec["status"] = "erro"
        rec["motivo"] = f"{type(e).__name__}: {str(e)[:200]}"
        return rec


# ----------------------------------------------------------------- rodada

SEED = 20260721


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Runner do baseline de performance")
    ap.add_argument("--smoke", action="store_true", help="dry-run: toda celula em R<=100")
    ap.add_argument("--only", help="blocos a rodar (ex: B1,B2)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--stamp-utc", default=None, help="timestamp ISO (reprodutibilidade)")
    args = ap.parse_args(argv)

    cases_path = AQUI / "cases.json"
    cj = json.loads(cases_path.read_text(encoding="utf-8"))
    casos = cj["casos"]
    if args.only:
        alvo = set(args.only.split(","))
        casos = [c for c in casos if set(c.get("blocos", [])) & alvo]

    man = MAN.gerar()
    if man["git"]["dirty"] and not args.smoke:
        print("AVISO: arvore git suja — baseline nao e' reproduzivel (ok em --smoke)")

    stamp = args.stamp_utc or datetime.now(timezone.utc).isoformat()
    drift = CAL.DriftTracker()
    print(f"[perf] {len(casos)} casos {'(SMOKE)' if args.smoke else ''} · "
          f"calibrando maquina...", flush=True)
    calib = CAL.medir_calibradores()

    registros: list[dict] = []
    contagem = {"ok": 0, "pendente": 0, "rejeitado": 0, "erro": 0, "rt-quebrado": 0}
    for i, case in enumerate(casos):
        if i % SENTINELA_CADA == 0:
            drift.bater(i)                                     # deriva termica
        rec = run_case(case, i, args.smoke)
        rec["manifest_git"] = man["git"]["head"][:12]
        rec["stamp_utc"] = stamp
        registros.append(rec)
        contagem[rec.get("status", "erro")] = contagem.get(rec.get("status", "erro"), 0) + 1
        st = rec.get("status")
        if st == "ok":
            e = rec["encode"]
            print(f"  [{i+1}/{len(casos)}] {rec['case_id'][:48]:<48} "
                  f"enc={e['point_ns']/1e6:.2f}ms tier={e['tier']} n={e['n']}", flush=True)
        else:
            print(f"  [{i+1}/{len(casos)}] {rec['case_id'][:48]:<48} {st}: "
                  f"{rec.get('motivo','')[:40]}", flush=True)
    drift.bater(len(casos))

    SAIDA.mkdir(parents=True, exist_ok=True)
    tag = "smoke" if args.smoke else "baseline"
    out = Path(args.out) if args.out else SAIDA / f"perf-{tag}.jsonl"
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for r in registros:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    resumo = {
        "schema": "perf-baseline-09/run-v1", "tag": tag, "stamp_utc": stamp,
        "manifest": man, "calibradores": calib, "drift": drift.resumo(),
        "contagem": contagem, "n_casos": len(casos),
    }
    (out.with_suffix(".run.json")).write_text(
        json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    print(f"\n{contagem}  ->  {out}")
    d = resumo["drift"]
    if d:
        print(f"drift: ratio_max={d['drift_ratio_max']} noise_floor_cv={d['noise_floor_cv']} "
              f"{'TERMICAMENTE SUSPEITO' if d['thermally_suspect'] else 'estavel'}")
    return 0 if contagem["erro"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
