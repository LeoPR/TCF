"""Runner do baseline — o PROCESSO cristalizado (schema perf-baseline-09/run-v3).

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
import time
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
from bench_perf import plans as PL                               # noqa: E402

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


# ----------------------------------------------------------------- medicao de 1 caso

# ----------------------------------------------------------------- concorrencia (B4)
# Presets multi-col que aproximam adult/lineitem em (n_cols, n_rows). Perfil MISTO:
# colunas de custo variado, pra a "coluna mais cara" (que limita o paralelismo
# por-coluna do TCF) aparecer — e' a hipotese do owner sobre saturacao interna.
_MC_PRESETS = {"adult-20k": (15, 20000), "lineitem-20k": (16, 20000)}
_MC_FORMAS = ("free-text", "structured", "low-entropy", "flat-mixed")


def _synth_multicol(R: int, C: int, seed: int) -> V.Pivot:
    piv: V.Pivot = {}
    for c in range(C):
        col = SY.synth_pivot(R, 1, 32, 0.1, _MC_FORMAS[c % len(_MC_FORMAS)], seed=seed + c * 13)
        piv[f"col{c:02d}"] = col["col00"]
    return piv


def _worker_min_encode(payload) -> int:
    """Roda num PROCESSO separado (test-concurrency). Reconstroi o dado (spawn
    re-importa) e devolve o MIN de `reps` encodes — steady-state, sem o spawn."""
    R, C, seed, reps = payload
    from tcf import encode
    piv = _synth_multicol(R, C, seed)
    best = 1 << 62
    for _ in range(reps):
        t0 = time.perf_counter_ns()
        encode(piv)
        dt = time.perf_counter_ns() - t0
        if dt < best:
            best = dt
    return best


def _mc_dims(case: dict, smoke: bool) -> tuple[int, int]:
    C, R = _MC_PRESETS.get(case["fonte"], (8, 20000))
    return (200 if smoke else R), C


def _run_concorrencia(case: dict, rec: dict, vet: dict, smoke: bool) -> dict:
    from tcf import encode, decode
    R, C = _mc_dims(case, smoke)
    piv = _synth_multicol(R, C, SEED)
    V.g1_retangular(piv)
    interno = vet["concorrencia"]["internal"]     # serial|p2|p4|p8
    teste = vet["concorrencia"]["test"]           # t1|t2|t4|t8
    workers = int(interno[1:]) if interno.startswith("p") else 1
    kproc = int(teste[1:]) if teste.startswith("t") else 1

    # RT gate (com o parallel pedido) — sem RT, nenhum numero
    blob = encode(piv, parallel=workers) if workers > 1 else encode(piv)
    if decode(blob) != piv:
        rec["status"] = "rt-quebrado"; rec["motivo"] = "RT sob parallel falhou"; return rec
    rec["rt_ok"] = True
    rec["bytes"] = len(blob.encode("utf-8"))
    rec["workload"] = SY.descrever(piv)
    rec["concorrencia"] = {"internal_workers": workers, "test_procs": kproc, "n_cols": C}

    if vet["granularidade"] == "process-tree":
        # memoria da ARVORE de processos: tracemalloc do pai nao ve os filhos, e
        # somar RSS por-PID sem psutil (stdlib-only) e' fragil no Windows.
        rec["status"] = "pendente"
        rec["motivo"] = "memoria de arvore de processos precisa de psutil (stdlib nao soma filhos)"
        return rec

    # EIXO 1 — paralelismo INTERNO: encode(parallel=N). cpu_wall_ratio revela se
    # o paralelo AJUDOU (>1 = trabalho real concorrente) ou nem rodou (~1 serial).
    if workers > 1:
        rec["encode"] = P.medir(lambda: encode(piv, parallel=workers))
        rec["encode_serial_ref"] = P.medir(lambda: encode(piv))
        eb = rec["encode"]["point_ns"]; sb = rec["encode_serial_ref"]["point_ns"]
        rec["speedup_interno"] = round(sb / eb, 3) if eb else None
    else:
        rec["encode"] = P.medir(lambda: encode(piv))

    # EIXO 2 — paralelismo do TESTE: K encodes independentes concorrentes. Se o
    # interno satura no nº de colunas, disparar K processos pode escalar melhor.
    if kproc > 1:
        from concurrent.futures import ProcessPoolExecutor
        solo = rec["encode"]["min_ns"]
        payload = (R, C, SEED, 3)
        t0 = time.perf_counter_ns()
        try:
            with ProcessPoolExecutor(max_workers=kproc) as ex:
                mins = list(ex.map(_worker_min_encode, [payload] * kproc))
            batch_wall = time.perf_counter_ns() - t0
            med = sorted(mins)[len(mins) // 2]
            cont = (med / solo) if solo else None
            rec["test_concurrency"] = {
                "k": kproc,
                "solo_min_ns": solo,
                "por_worker_min_ns": mins,
                "mediana_min_ns": med,
                # SINAL LIMPO (steady-state): ~1 = K encodes independentes nao se atrapalham
                "contention_ratio": round(cont, 3) if cont else None,
                # escala efetiva: com contention~1, ~= K (paralelismo do teste paga)
                "escala_efetiva": round(kproc / cont, 2) if cont else None,
                "batch_wall_ns": batch_wall,
                # POLUIDO PELO SPAWN (Windows): o batch inclui o custo de criar K procs;
                # NAO e' o throughput steady-state. Use contention_ratio pra escalar.
                "batch_throughput_com_spawn": round((kproc * solo) / batch_wall, 3) if batch_wall else None,
            }
        except Exception as e:
            rec["test_concurrency_erro"] = f"{type(e).__name__}: {str(e)[:120]}"
    rec["status"] = "ok"
    return rec


# ----------------------------------------------------------------- candidate / column / accel (B3/B7)

def _run_candidate(case: dict, rec: dict, smoke: bool) -> dict:
    """Custo dos candidatos PERDEDORES do _best_of, via A/B fallback=True/False.
    fallback=True (default) roda _v2b/_struct_split completos por coluna; False pula."""
    from tcf import encode, decode
    piv = build_pivot(case, smoke)
    V.g1_retangular(piv)
    bt, bf = encode(piv), encode(piv, fallback=False)
    rec["rt_ok"] = (decode(bt) == piv and decode(bf) == piv)
    rec["bytes"], rec["bytes_no_candidates"] = len(bt.encode()), len(bf.encode())
    rec["workload"] = SY.descrever(piv)
    if not rec["rt_ok"]:
        rec["status"] = "rt-quebrado"; rec["motivo"] = "RT falhou (fallback T/F)"; return rec
    rec["encode"] = P.medir(lambda: encode(piv))                   # com candidatos (default)
    rec["encode_no_candidates"] = P.medir(lambda: encode(piv, fallback=False))
    et, ef = rec["encode"]["point_ns"], rec["encode_no_candidates"]["point_ns"]
    rec["candidate_overhead"] = round(et / ef, 3) if ef else None  # >1 = perdedores custam tempo
    rec["bytes_ganho_candidatos"] = rec["bytes_no_candidates"] - rec["bytes"]  # >0 = valeram bytes
    rec["status"] = "ok"; return rec


def _run_column(case: dict, rec: dict, smoke: bool) -> dict:
    """Decomposicao por coluna: cada coluna e' amostra independente do MESMO
    caminho de codigo em escala. Mede UMA coluna da tabela C8 (single-col)."""
    from tcf import encode, decode
    pid = case["vectors"]["escala"].get("point_id", "")
    idx = int(pid.split("col")[-1]) if "col" in pid else 0
    R = _escala(case, smoke).get("R", 100)
    piv = SY.synth_pivot(R, 8, 32, 0.1, "flat-mixed", seed=SEED)
    name = f"col{idx:02d}"
    col = piv[name]
    blob = encode(col)                                             # single-col (list)
    rec["rt_ok"] = decode(blob) == col
    rec["bytes"] = len(blob.encode())
    rec["coluna"], rec["n_valores"], rec["n_unicos"] = name, len(col), len(set(col))
    if not rec["rt_ok"]:
        rec["status"] = "rt-quebrado"; return rec
    rec["encode"] = P.medir(lambda: encode(col))
    rec["decode"] = P.medir(lambda: decode(blob))
    rec["status"] = "ok"; return rec


def _worker_pure_encode(payload):
    """Subprocesso: restaura o detector PURE-Python (monkeypatch global contamina),
    encoda, devolve (min_ns, bytes). O byte tem que bater com o Cython."""
    R, C, L, K, forma, reps = payload
    from tcf.composicional.syntax import M8AVirtualRefsSyntax as M
    M._detect_compositions = M._detect_compositions_py
    M._detect_compositions_accelerated = False
    from tcf import encode
    piv = _mc_or_synth(R, C, L, K, forma)
    best, blob = 1 << 62, None
    for _ in range(reps):
        t0 = time.perf_counter_ns()
        blob = encode(piv)
        dt = time.perf_counter_ns() - t0
        if dt < best:
            best = dt
    return best, len(blob.encode("utf-8"))


def _mc_or_synth(R, C, L, K, forma):
    return SY.synth_pivot(R, C, L, K, forma, seed=SEED)


def _run_accel(case: dict, rec: dict, smoke: bool) -> dict:
    """A/B Cython vs pure-Python do detector HCC. O '2.1-2.3x' vivia num comentario;
    aqui e' curva medida. Pure roda em SUBPROCESSO (patch global). Gate: bytes iguais."""
    from tcf import encode, decode
    from tcf.composicional.syntax import M8AVirtualRefsSyntax as M
    e, forma = _escala(case, smoke), case["vectors"]["forma"]
    R, C, L, K = e.get("R", 100), e.get("C", 4), e.get("L", 32), e.get("K", 0.1)
    piv = _mc_or_synth(R, C, L, K, forma)
    blob = encode(piv)
    rec["rt_ok"] = decode(blob) == piv
    rec["bytes"] = len(blob.encode())
    rec["cython_ativo"] = bool(getattr(M, "_detect_compositions_accelerated", False))
    if not rec["rt_ok"]:
        rec["status"] = "rt-quebrado"; return rec
    rec["encode"] = P.medir(lambda: encode(piv))                  # cython (in-process)
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=1) as ex:
        pure_min, pure_bytes = ex.submit(_worker_pure_encode, (R, C, L, K, forma, 5)).result()
    rec["accel_pure_min_ns"] = pure_min
    rec["accel_bytes_identicos"] = (pure_bytes == rec["bytes"])   # cython == pure (gate ADR-0020)
    cm = rec["encode"]["min_ns"]
    rec["speedup_cython"] = round(pure_min / cm, 3) if cm else None
    if not rec["cython_ativo"]:
        rec["motivo"] = "cython nao carregado — speedup ~1 (ambos puros)"
    rec["status"] = "ok"; return rec


_ENVELOPE_FONTES = {"sentinela", "sondas"}   # B0: infra do run, nao celula de dado


def run_case(case: dict, order_index: int, smoke: bool) -> dict:
    cid = case["case_id"]
    vet = case["vectors"]
    rec: dict = {
        "case_id": cid, "blocos": case.get("blocos", []), "order_index": order_index,
        "vectors": vet, "fonte": case["fonte"],
    }

    # B0 como ENVELOPE (parecer §3): pins/sondas/sentinela VALIDAM a rodada
    # (manifesto + calibrador + sentinela ja' fazem isso no cabecalho), nao sao
    # workload de produto. Status proprio, FORA da contagem de comparaveis — nao
    # 'pendente' artificial.
    fonte = case["fonte"]
    if fonte in _ENVELOPE_FONTES or fonte.startswith("pin-"):
        rec["status"] = "envelope"
        rec["motivo"] = "regua/infra do run (manifesto+calibrador validam); nao e' celula comparavel"
        return rec

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
                from tcf import encode as _enc, decode as _dec   # API unica: encode rota .8H
                ser, des = _enc, _dec
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

    if cam not in CAMINHOS:
        rec["status"] = "pendente"
        rec["motivo"] = f"caminho '{cam}' desconhecido"
        return rec
    # CONCORRENCIA (B4): paralelismo interno (encode parallel=N) x do teste (K procs)
    if vet["concorrencia"]["internal"] != "serial" or vet["concorrencia"]["test"] != "t1" \
            or vet["granularidade"] == "process-tree":
        if vet["accel"] != "cython" or vet["compressao"] != "none":
            rec["status"] = "pendente"; rec["motivo"] = "concorrencia + accel/compressao pendente"
            return rec
        try:
            return _run_concorrencia(case, rec, vet, smoke)
        except Exception as e:
            rec["status"] = "erro"; rec["motivo"] = f"{type(e).__name__}: {str(e)[:200]}"
            return rec

    if vet["granularidade"] == "candidate":
        try:
            return _run_candidate(case, rec, smoke)
        except Exception as e:
            rec["status"] = "erro"; rec["motivo"] = f"{type(e).__name__}: {str(e)[:200]}"; return rec
    if vet["granularidade"] == "column":
        try:
            return _run_column(case, rec, smoke)
        except Exception as e:
            rec["status"] = "erro"; rec["motivo"] = f"{type(e).__name__}: {str(e)[:200]}"; return rec
    if vet["accel"] == "pure":
        try:
            return _run_accel(case, rec, smoke)
        except Exception as e:
            rec["status"] = "erro"; rec["motivo"] = f"{type(e).__name__}: {str(e)[:200]}"; return rec

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
        t0 = time.perf_counter_ns()
        pivot = build_pivot(case, smoke)
        V.g1_retangular(pivot)
        obj, ser, des = CAMINHOS[cam](pivot)
        rec["prepare_ns"] = time.perf_counter_ns() - t0

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


def avaliar_rodada(por_id: dict[str, str], opcionais: "set[str] | None",
                   n_casos_total: int, thermally_suspect: bool) -> dict:
    """Decisao de status a partir dos status por case_id — PURA (testavel isolada).

    DUAS dimensoes ORTOGONAIS (parecer 2340 §1 — o termico NAO e' o status final):
      - `status` = VALIDADE DE DADOS: 'completo' | 'parcial'. correcao (rt-quebrado/
        erro) SEMPRE invalida; com plano, caso NAO-opcional fora de ok/envelope
        invalida; opcional pode ficar pendente sem invalidar.
      - `runner_thermal_status` = ESTABILIDADE do ambiente: 'estavel' |
        'termicamente-suspeito'. E' um AVISO do gate intra-run, NAO um veredito de
        validade. Um run pode ser 'completo' E 'termicamente-suspeito' — comparavel
        first-order (o comparador avisa, nao bloqueia; --strict-thermal p/ precisao).
    """
    contagem: dict[str, int] = {}
    for st in por_id.values():
        contagem[st] = contagem.get(st, 0) + 1
    n_registro = len(por_id)
    obrig_falhou = 0
    if opcionais is not None:
        obrig_falhou = sum(1 for cid, st in por_id.items()
                           if cid not in opcionais and st not in ("ok", "envelope"))
    rt_q = contagem.get("rt-quebrado", 0)
    err = contagem.get("erro", 0)
    tudo_registrado = n_registro >= n_casos_total
    sao = tudo_registrado and rt_q == 0 and err == 0 and obrig_falhou == 0
    status = "completo" if sao else "parcial"
    thermal = "termicamente-suspeito" if thermally_suspect else "estavel"
    return {"status": status, "runner_thermal_status": thermal,
            "contagem": contagem, "n_registro": n_registro,
            "n_comparavel": contagem.get("ok", 0), "n_envelope": contagem.get("envelope", 0),
            "rt_q": rt_q, "err": err, "obrig_falhou": obrig_falhou}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Runner do baseline de performance")
    ap.add_argument("--smoke", action="store_true", help="dry-run: toda celula em R<=100")
    ap.add_argument("--only", help="blocos a rodar (ex: B1,B2)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--stamp-utc", default=None, help="timestamp ISO (reprodutibilidade)")
    ap.add_argument("--resume", action="store_true",
                    help="continua um JSONL existente: pula case_id ja' feitos (mesmo git+matriz)")
    ap.add_argument("--probative", action="store_true",
                    help="rodada de EVIDENCIA: fail-closed — aborta antes se arvore suja OU cython "
                         "ausente; ao fim, exit!=0 se os DADOS nao ficarem 'completo' (o termico "
                         "e' aviso, nao bloqueia)")
    ap.add_argument("--strict-thermal", action="store_true",
                    help="com --probative: exige tambem estabilidade termica (falha se "
                         "termicamente-suspeito). Default: termico e' so' aviso (first-order).")
    ap.add_argument("--plan", help="plano de execucao (nucleo/campanha/smoke): seleciona casos + "
                                   "aceite obrigatorio/opcional (matriz-mestra intocada)")
    args = ap.parse_args(argv)

    cases_path = AQUI / "cases.json"
    cj = json.loads(cases_path.read_text(encoding="utf-8"))
    casos = cj["casos"]

    man = MAN.gerar()
    git12 = man["git"]["head"][:12]
    cases12 = str(man.get("cases_sha256"))[:12]

    # PLANO (Fase 3b): a cadencia, separada da matriz. Seleciona um subconjunto +
    # declara intencao e aceite. O plano e' PRA ESTA matriz (pin) — se a matriz
    # mudou, o plano nao vale.
    plano = plano_sha = opcionais = None
    if args.plan:
        plano = PL.carregar(args.plan)
        if not PL.pin_ok(plano, man.get("cases_sha256")):
            print(f"ABORTA: plano '{args.plan}' e' pra outra matriz "
                  f"(pin {str(plano.get('pin_cases_sha256'))[:12]} != {cases12}).")
            return 4
        plano_sha = PL.hash_plano(plano)
        casos = PL.selecionar(plano, casos)
        opcionais = {c["case_id"] for c in casos if PL.e_opcional(plano, c)}
        print(f"[plano {args.plan}] intencao={plano.get('intencao')} · {len(casos)} casos "
              f"({len(opcionais)} opcionais) · campanha={plano.get('campanha')}", flush=True)
    elif args.only:
        alvo = set(args.only.split(","))
        casos = [c for c in casos if set(c.get("blocos", [])) & alvo]

    # PRE-GATE PROBATORIO (parecer §3, fail-closed): uma rodada de evidencia so'
    # comeca de commit LIMPO e com o acelerador da distribuicao ATIVO. Aborta ANTES,
    # nao mede lixo. Fora de --probative, so' avisa (desenvolvimento).
    problemas = []
    if man["git"]["dirty"]:
        problemas.append("arvore git SUJA (baseline nao reproduzivel)")
    if not man.get("cython_accel"):
        problemas.append("acelerador Cython AUSENTE (casos 'cython' mediriam pure-Python)")
    if problemas:
        if args.probative:
            print("ABORTA (probatorio): " + " · ".join(problemas)
                  + ". Corrija antes de rodar evidencia.")
            return 3
        if not args.smoke:
            print("AVISO: " + " · ".join(problemas) + " (ok em --smoke; use --probative p/ evidencia)")

    stamp = args.stamp_utc or datetime.now(timezone.utc).isoformat()
    SAIDA.mkdir(parents=True, exist_ok=True)
    # artefato proprio por plano (Fase 3c: cada cadencia = arquivo/resumo proprios).
    # smoke SEMPRE no tag -> artefato smoke (dados R<=100 de brinquedo) nunca compartilha
    # arquivo com um baseline real, nem se mistura nele via --resume.
    tag = (f"{args.plan}-smoke" if args.smoke else args.plan) if args.plan \
        else ("smoke" if args.smoke else "baseline")
    out = Path(args.out) if args.out else SAIDA / f"perf-{tag}.jsonl"
    sentinela_cada = (plano.get("sentinela_cada", SENTINELA_CADA) if plano else SENTINELA_CADA)

    # RETOMADA (parecer §4): persistencia incremental deixa o JSONL parcial. Aqui
    # so' retomamos registros do MESMO codigo+matriz — misturar .8-velho com
    # .8-novo produziria um baseline cientificamente desigual.
    feitos: set[str] = set()
    if args.resume and out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("manifest_git") == git12 and r.get("cases_sha") == cases12:
                feitos.add(r["case_id"])
            else:
                print(f"ABORTA retomada: registro {r.get('case_id','?')[:40]} de git/matriz "
                      f"DIFERENTE ({r.get('manifest_git')} vs {git12}). Comece um artefato novo.")
                return 2
        print(f"[resume] {len(feitos)} casos ja' feitos serao pulados", flush=True)

    drift = CAL.DriftTracker()
    print(f"[perf] {len(casos)} casos {'(SMOKE)' if args.smoke else ''} · calibrando...", flush=True)
    calib = CAL.medir_calibradores()

    fh = out.open("a" if feitos else "w", encoding="utf-8", newline="\n")
    n_medido = 0
    try:
        for i, case in enumerate(casos):
            if case["case_id"] in feitos:
                continue                                       # ja' feito (retomada)
            if n_medido % sentinela_cada == 0:
                drift.bater(i)                                 # deriva termica
            rec = run_case(case, i, args.smoke)
            rec["smoke"] = bool(args.smoke)                    # proveniencia: smoke != baseline
            rec["manifest_git"] = git12
            rec["cases_sha"] = cases12                         # (git, matriz) verificados na retomada
            rec["stamp_utc"] = stamp
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()                                         # INCREMENTAL: sobrevive a morte
            n_medido += 1
            st = rec.get("status")
            if st == "ok":
                e = rec["encode"]
                print(f"  [{i+1}/{len(casos)}] {rec['case_id'][:46]:<46} "
                      f"enc={e['point_ns']/1e6:.2f}ms tier={e['tier']}", flush=True)
            else:
                print(f"  [{i+1}/{len(casos)}] {rec['case_id'][:46]:<46} {st}: "
                      f"{rec.get('motivo','')[:38]}", flush=True)
        drift.bater(len(casos))
    finally:
        fh.close()                                             # o JSONL fica valido mesmo se morrer

    # RESUMO: le o JSONL COMPLETO (feitos + novos), dedup por case_id (ultimo vence)
    por_id: dict[str, str] = {}
    for line in out.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        por_id[r["case_id"]] = r.get("status", "erro")
    d = drift.resumo()
    av = avaliar_rodada(por_id, opcionais, len(casos),
                        thermally_suspect=bool(d and d.get("thermally_suspect")))
    status = av["status"]
    thermal = av["runner_thermal_status"]
    contagem = av["contagem"]
    n_registro = av["n_registro"]
    n_comparavel = av["n_comparavel"]
    n_envelope = av["n_envelope"]
    rt_q, err, obrig_falhou = av["rt_q"], av["err"], av["obrig_falhou"]

    resumo = {
        "schema": "perf-baseline-09/run-v3", "tag": tag, "smoke": bool(args.smoke),
        # VALIDADE DE DADOS (status) e ESTABILIDADE (runner_thermal_status) sao ORTOGONAIS
        # (parecer 2340 §1). O termico e' AVISO, nao veredito — o comparador nao bloqueia
        # por ele (salvo --strict-thermal).
        "status": status, "runner_thermal_status": thermal,
        "stamp_utc": stamp,
        "manifest": man, "calibradores": calib, "drift": d,
        "n_casos_total": len(casos), "n_com_registro": n_registro,
        "n_comparaveis_ok": n_comparavel, "n_envelope": n_envelope,
        "n_obrig_falhou": obrig_falhou, "n_opcional": (len(opcionais) if opcionais else 0),
        "contagem": contagem,
        # PLANO (Fase 3b): a CADENCIA vira parte da identidade da rodada. Duas rodadas
        # so' sao comparaveis se compartilham plano_sha + intencao (o comparador exige).
        "plano": ({"id": plano.get("plan_id"), "sha": plano_sha,
                   "intencao": plano.get("intencao"),
                   "campanha": bool(plano.get("campanha"))} if plano else None),
        "nota_adjudicacao": ("status=validade-de-dados; runner_thermal_status=estabilidade "
                             "intra-run (AVISO). 'termicamente-suspeito' NAO invalida — first-order "
                             "aceita via analise entre-runs (piloto). --strict-thermal exige estavel."),
        "nota_drift": "drift e' da SESSAO atual; retomada cross-sessao nao unifica (bloco = Fase 3)",
    }
    (out.with_suffix(".run.json")).write_text(
        json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    print(f"\nstatus={status}  termico={thermal}  comparaveis(ok)={n_comparavel}  "
          f"envelope={n_envelope}  registro={n_registro}/{len(casos)}  {contagem}  ->  {out}")
    if d:
        print(f"drift: ratio_max={d['drift_ratio_max']} noise_floor_cv={d['noise_floor_cv']} "
              f"{'TERMICAMENTE SUSPEITO (aviso, nao bloqueia)' if d['thermally_suspect'] else 'estavel'}")

    # RETURN FAIL-CLOSED: correcao (erro/rt-quebrado) SEMPRE falha; probatoria exige
    # VALIDADE DE DADOS ('completo'). O termico e' AVISO — so' falha em --strict-thermal.
    if err or rt_q:
        print(f"FALHA: {err} erro + {rt_q} rt-quebrado — evidencia invalida.")
        return 1
    if args.probative and status != "completo":
        print(f"FALHA (probatorio): status={status} (dados incompletos) — nao serve como referencia.")
        return 1
    if args.probative and n_comparavel == 0:
        print("FALHA (probatorio): 0 celulas comparaveis (so' envelope/opcional) — sem numero pra referenciar.")
        return 1
    if args.probative and args.strict_thermal and thermal != "estavel":
        print(f"FALHA (--strict-thermal): {thermal} — exigida estabilidade termica.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
