"""Testes de contrato do bench_perf — poucos, mas com dentes (parecer Fase 3d).

Cobrem as INVARIANTES que, se quebrarem, deixam concluir bobagem:
  - planos: selecao por predicado, opcional, hash canonico, pin, disjuncao nucleo/campanha;
  - avaliar_rodada: obrigatorio/opcional, rt-quebrado sempre invalida, termico reprova antes;
  - comparador: recusa matriz/plano/intencao/status divergentes (fail-closed) e o autoteste.

Roda sem pytest:  python -m bench_perf.tests.test_contrato
Tambem e' descoberto por pytest (funcoes test_*).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from bench_perf import plans as PL
from bench_perf import compare as CMP
from bench_perf.runner import avaliar_rodada

AQUI = Path(__file__).resolve().parent
CASES = json.loads((AQUI.parent / "cases.json").read_text(encoding="utf-8"))["casos"]
PIN = "de10e05252cb5463ee6a303c8c8105ee289bda4c86b23630d20ae9ac8f761432"


# ------------------------------------------------------------------ planos ---
def test_nucleo_exclui_caro():
    """Nucleo (referencia recorrente barata) NAO pode conter B4, R6e5 nem process-tree."""
    plano = PL.carregar("nucleo")
    sel = PL.selecionar(plano, CASES)
    assert sel, "nucleo selecionou zero casos"
    for c in sel:
        assert "B4" not in c["blocos"], f"B4 vazou pro nucleo: {c['case_id']}"
        assert c["vectors"]["escala"].get("point_id") != "R6e5", c["case_id"]
        assert c["vectors"].get("granularidade") != "process-tree", c["case_id"]


def test_campanha_pega_o_caro():
    """Campanha existe pro que e' caro: cada caso tem B4 OU R6e5 OU process-tree."""
    plano = PL.carregar("campanha")
    sel = PL.selecionar(plano, CASES)
    assert sel, "campanha selecionou zero casos"
    for c in sel:
        caro = ("B4" in c["blocos"]
                or c["vectors"]["escala"].get("point_id") == "R6e5"
                or c["vectors"].get("granularidade") == "process-tree")
        assert caro, f"caso barato na campanha: {c['case_id']}"


def test_nucleo_e_campanha_disjuntos():
    """Um caso nao pode ser contado nas DUAS cadencias (senao dupla-contagem de evidencia)."""
    n = {c["case_id"] for c in PL.selecionar(PL.carregar("nucleo"), CASES)}
    k = {c["case_id"] for c in PL.selecionar(PL.carregar("campanha"), CASES)}
    assert not (n & k), f"casos em nucleo E campanha: {sorted(n & k)[:3]}"


def test_opcional_nao_e_obrigatorio():
    """process-tree e' opcional na campanha (memoria multiproc pode faltar sem invalidar)."""
    plano = PL.carregar("campanha")
    algum_pt = [c for c in PL.selecionar(plano, CASES)
                if c["vectors"].get("granularidade") == "process-tree"]
    assert algum_pt, "esperava process-tree na campanha"
    for c in algum_pt:
        assert PL.e_opcional(plano, c), f"process-tree devia ser opcional: {c['case_id']}"


def test_hash_e_da_identidade_nao_da_prosa():
    """Hash = IDENTIDADE (selecao+versao+pin), independente de ordem de chave. Editar
    descricao/intencao (prosa/semantica) NAO muda o sha; mudar a SELECAO muda."""
    plano = PL.carregar("nucleo")
    baralhado = dict(reversed(list(plano.items())))
    assert PL.hash_plano(plano) == PL.hash_plano(baralhado)          # ordem nao importa
    # prosa/intencao NAO entram (senao um typo na descricao quebraria a comparacao .9)
    assert PL.hash_plano(dict(plano, descricao="typo corrigido")) == PL.hash_plano(plano)
    assert PL.hash_plano(dict(plano, intencao="outra-coisa")) == PL.hash_plano(plano)
    # a SELECAO entra: mexer em incluir/excluir/opcional muda o sha
    assert PL.hash_plano(dict(plano, excluir=[])) != PL.hash_plano(plano)


def test_pin_amarra_a_matriz():
    plano = PL.carregar("nucleo")
    assert plano["pin_cases_sha256"] == PIN
    assert PL.pin_ok(plano, PIN)
    assert not PL.pin_ok(plano, "matriz-diferente")
    assert PL.pin_ok({}, "qualquer-coisa")           # sem pin => nao trava


# --------------------------------------------------------- avaliar_rodada ---
def test_completo_exige_zero_rt_quebrado():
    por_id = {"a": "ok", "b": "ok", "c": "rt-quebrado"}
    av = avaliar_rodada(por_id, opcionais=set(), n_casos_total=3, thermally_suspect=False)
    assert av["status"] == "parcial", "rt-quebrado tem que derrubar 'completo'"
    assert av["rt_q"] == 1


def test_obrigatorio_pendente_invalida_mas_opcional_nao():
    # 'x' opcional pode ficar pendente; 'y' obrigatorio pendente derruba
    por_id = {"x": "pendente", "y": "ok"}
    assert avaliar_rodada(por_id, {"x"}, 2, False)["status"] == "completo"
    por_id2 = {"x": "pendente", "y": "pendente"}
    av = avaliar_rodada(por_id2, {"x"}, 2, False)
    assert av["status"] == "parcial"
    assert av["obrig_falhou"] == 1


def test_termico_ortogonal_ao_status():
    # DESACOPLADO (parecer 2340 §1): termico-suspeito NAO invalida os dados —
    # status fica 'completo' e o termico vira campo proprio (aviso).
    por_id = {"a": "ok", "b": "ok"}
    av = avaliar_rodada(por_id, set(), 2, thermally_suspect=True)
    assert av["status"] == "completo"
    assert av["runner_thermal_status"] == "termicamente-suspeito"
    # sem suspeita -> estavel
    av2 = avaliar_rodada(por_id, set(), 2, thermally_suspect=False)
    assert av2["status"] == "completo" and av2["runner_thermal_status"] == "estavel"
    # dados parciais + termico-suspeito: status=parcial, termico=suspeito (ortogonais)
    av3 = avaliar_rodada({"a": "ok"}, set(), 2, thermally_suspect=True)  # falta 1 registro
    assert av3["status"] == "parcial" and av3["runner_thermal_status"] == "termicamente-suspeito"


def test_sem_plano_tolera_pendente():
    # opcionais=None (rodada sem --plan): pendente nao invalida, so' erro/rt-quebrado
    por_id = {"a": "ok", "b": "pendente"}
    assert avaliar_rodada(por_id, None, 2, False)["status"] == "completo"


# ---------------------------------------------------------------- compare ---
def _rec(cid, ns, tier="micro", n=31, status="ok"):
    return {"case_id": cid, "status": status,
            "encode": {"point_ns": ns, "tier": tier, "n": n, "mde_pct": 5.0}}


def _run(cases_sha="AAA", plano_sha="P1", intencao="referencia-recorrente-comparavel",
         status="completo", thermal="estavel"):
    return {"status": status, "runner_thermal_status": thermal,
            "manifest": {"cases_sha256": cases_sha},
            "calibradores": {"C1": {"point_ns": 100}}, "drift": {"noise_floor_cv": 0.0},
            "plano": {"id": "nucleo", "sha": plano_sha, "intencao": intencao, "campanha": False}}


def _escreve(d: Path, nome: str, recs, resumo) -> Path:
    p = d / f"{nome}.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in recs), encoding="utf-8")
    p.with_suffix(".run.json").write_text(json.dumps(resumo), encoding="utf-8")
    return p


def _com_tmp(fn):
    with tempfile.TemporaryDirectory() as td:
        fn(Path(td))


def test_compare_matriz_igual_e_ruido_dentro_do_limiar():
    def corpo(d: Path):
        recs = [_rec("k1", 1000), _rec("k2", 2000)]
        a = _escreve(d, "a", recs, _run())
        b = _escreve(d, "b", [_rec("k1", 1010), _rec("k2", 2010)], _run())  # ~1% < limiar 5%
        r = CMP.comparar(a, b)
        assert r["matriz_igual"] and r["plano_igual"] and r["intencao_igual"]
        assert r["contagem"]["PIOR"] == 0 and r["contagem"]["MELHOR"] == 0
    _com_tmp(corpo)


def test_compare_recusa_matriz_diferente():
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("k1", 1000)], _run(cases_sha="AAA"))
        b = _escreve(d, "b", [_rec("k1", 1000)], _run(cases_sha="BBB"))
        assert CMP.comparar(a, b)["matriz_igual"] is False
    _com_tmp(corpo)


def test_compare_recusa_plano_diferente():
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("k1", 1000)], _run(plano_sha="P1"))
        b = _escreve(d, "b", [_rec("k1", 1000)], _run(plano_sha="P2"))
        r = CMP.comparar(a, b)
        assert r["matriz_igual"] and r["plano_igual"] is False
    _com_tmp(corpo)


def test_compare_recusa_intencao_diferente():
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("k1", 1000)], _run(intencao="referencia-recorrente-comparavel"))
        b = _escreve(d, "b", [_rec("k1", 1000)], _run(intencao="caracterizacao-fotografia"))
        assert CMP.comparar(a, b)["intencao_igual"] is False
    _com_tmp(corpo)


def test_compare_protocolo_desigual():
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("k1", 1000, tier="micro", n=31)], _run())
        b = _escreve(d, "b", [_rec("k1", 1000, tier="small", n=15)], _run())
        r = CMP.comparar(a, b)
        assert r["contagem"]["protocolo-desigual"] == 1
    _com_tmp(corpo)


def test_compare_detecta_pior_alem_do_limiar():
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("k1", 1000)], _run())
        b = _escreve(d, "b", [_rec("k1", 1200)], _run())            # +20% > limiar 5%
        r = CMP.comparar(a, b)
        assert r["contagem"]["PIOR"] == 1
    _com_tmp(corpo)


def test_compare_termico_suspeito_e_comparavel_por_default():
    # DESACOPLADO: um lado termico-suspeito mas com DADOS completos NAO invalida a
    # comparacao (first-order). validade=completo dos dois lados; termico=suspeito no b.
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("k1", 1000)], _run(thermal="estavel"))
        b = _escreve(d, "b", [_rec("k1", 1010)], _run(thermal="termicamente-suspeito"))
        r = CMP.comparar(a, b)
        assert r["validade"] == {"baseline": "completo", "candidato": "completo"}
        assert r["status_termico"]["candidato"] == "termicamente-suspeito"
        # nenhum campo de validade bloqueia -> a comparacao procede (nao ha n/a por status)
        assert r["contagem"]["n/a"] == 0
    _com_tmp(corpo)


def test_compare_dados_parciais_invalidam():
    # validade!=completo BLOQUEIA (o main recusa) — aqui checamos o campo validade
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("k1", 1000)], _run(status="parcial"))
        b = _escreve(d, "b", [_rec("k1", 1000)], _run())
        assert CMP.comparar(a, b)["validade"]["baseline"] == "parcial"
    _com_tmp(corpo)


def test_adj_compat_schema_antigo():
    # run-v2 antigo: status='termicamente-reprovado' -> (completo, suspeito)
    assert CMP._adj({"status": "termicamente-reprovado"}) == ("completo", "termicamente-suspeito")
    # run-v2 completo sem campo termico -> estavel
    assert CMP._adj({"status": "completo"}) == ("completo", "estavel")
    # run-v3 novo: le os dois campos direto
    assert CMP._adj({"status": "completo", "runner_thermal_status": "termicamente-suspeito"}) \
        == ("completo", "termicamente-suspeito")


# ------------------------------------------------------------------- main ---
def _todos_testes():
    return [v for k, v in sorted(globals().items())
            if k.startswith("test_") and callable(v)]


def main() -> int:
    falhas = []
    testes = _todos_testes()
    for t in testes:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except Exception as e:                                     # noqa: BLE001
            falhas.append((t.__name__, e))
            print(f"  FALHA {t.__name__}: {e}")
    print(f"\n{len(testes) - len(falhas)}/{len(testes)} passaram")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
