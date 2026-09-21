"""Testes de contrato do bench_perf — poucos, mas com dentes (parecer Fase 3d).

Cobrem as INVARIANTES que, se quebrarem, deixam concluir bobagem:
  - planos: selecao por predicado, opcional, hash canonico, pin, disjuncao nucleo/campanha;
  - avaliar_rodada: obrigatorio/opcional, rt-quebrado sempre invalida, termico reprova antes;
  - comparador: recusa matriz/plano/intencao/status divergentes (fail-closed) e o autoteste;
    veredito pela razao caso/referencia dentro da rodada, calibrador so' sem referencia.

Roda sem pytest:  python -m bench_perf.tests.test_contrato
Tambem e' descoberto por pytest (funcoes test_*).
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from bench_perf import plans as PL
from bench_perf import compare as CMP
from bench_perf.manifest import sha_conteudo
from bench_perf.runner import avaliar_rodada, ordenar_vizinho

AQUI = Path(__file__).resolve().parent
CASES_PATH = AQUI.parent / "cases.json"
CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))["casos"]
# O pin e' o SHA-256 do CONTEUDO CANONIZADO do cases.json (2026-09-20), que e' o que o runner
# confere. Derivado do arquivo, o teste acusa pin velho no plano em vez de pedir uma constante
# a mais.
PIN = sha_conteudo(CASES_PATH)


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
         status="completo", thermal="estavel", piso=0.0, nota=None):
    return {"status": status, "runner_thermal_status": thermal,
            "nota_adjudicacao": nota,
            "manifest": {"cases_sha256": cases_sha},
            "calibradores": {"C1": {"point_ns": 100}}, "drift": {"noise_floor_cv": piso},
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


def test_referencias_cobrem_os_caminhos_ref_da_matriz():
    """Todo caminho de referencia da matriz esta' na lista que o comparador pareia."""
    caminhos = {c["case_id"].split("|", 1)[0] for c in CASES}
    refs = {c for c in caminhos if "-ref" in c}
    assert refs and refs <= set(CMP.REFERENCIAS), refs


def test_compare_referencia_cancela_a_maquina():
    """Maquina 30% mais lenta no lado B: caso e referencia inflam juntos, a razao nao se
    move. O fator do calibrador, igual nos dois lados, chamaria isso de PIOR."""
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("tcf-flat|x", 1000), _rec("csv-ref|x", 100)], _run())
        b = _escreve(d, "b", [_rec("tcf-flat|x", 1300), _rec("csv-ref|x", 130)], _run())
        r = CMP.comparar(a, b)
        assert r["normalizacao"] == "referencia"
        assert r["contagem"]["IGUAL"] == 1 and r["contagem"]["PIOR"] == 0
        assert r["contagem"]["controle"] == 1
    _com_tmp(corpo)


def test_compare_referencia_detecta_regressao_do_caso():
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("tcf-flat|x", 1000), _rec("csv-ref|x", 100)], _run())
        b = _escreve(d, "b", [_rec("tcf-flat|x", 1200), _rec("csv-ref|x", 100)], _run())
        r = CMP.comparar(a, b)
        assert r["contagem"]["PIOR"] == 1
        linha = next(ln for ln in r["linhas"] if ln["case_id"] == "tcf-flat|x")
        assert linha["pares_referencia"] == 1 and linha["delta_pct"] == 20.0
    _com_tmp(corpo)


def test_compare_sem_referencia_pareada_nao_vira_veredito():
    """Com referencia na rodada, o caso sem par de mesma cauda fica indecidivel."""
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("tcf-flat|y", 1000), _rec("csv-ref|x", 100)], _run())
        b = _escreve(d, "b", [_rec("tcf-flat|y", 2000), _rec("csv-ref|x", 100)], _run())
        r = CMP.comparar(a, b)
        assert r["contagem"]["sem-referencia"] == 1
        assert r["contagem"]["PIOR"] == 0 and r["contagem"]["MELHOR"] == 0
    _com_tmp(corpo)


def test_pin_por_conteudo_ignora_formatacao_e_pega_mudanca_real():
    """O pin responde "mudou algum CASO?", nao "mudou um byte do arquivo?"."""
    def corpo(d: Path):
        doc = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        a = d / "a.json"
        a.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        b = d / "b.json"   # mesma matriz, outra formatacao e outra ordem de chave
        b.write_text(json.dumps(doc, ensure_ascii=False, indent=4, sort_keys=True),
                     encoding="utf-8")
        assert sha_conteudo(a) == sha_conteudo(b), "reindentar nao pode invalidar o plano"
        assert hashlib.sha256(a.read_bytes()).hexdigest() != \
            hashlib.sha256(b.read_bytes()).hexdigest(), "o teste precisa de bytes diferentes"
        doc2 = json.loads(json.dumps(doc))
        doc2["casos"][0]["vectors"]["escala"]["R"] += 1     # mudanca REAL de um caso
        c = d / "c.json"
        c.write_text(json.dumps(doc2, ensure_ascii=False, indent=1), encoding="utf-8")
        assert sha_conteudo(c) != sha_conteudo(a), "mudar um caso TEM que quebrar o pin"
    _com_tmp(corpo)


def test_bytes_divergentes_invalida_como_rt_quebrado():
    """Saida do instrumentado != limpo, ou cython != puro, e' correcao, nao desempenho."""
    por_id = {"a": "ok", "b": "bytes-divergentes"}
    av = avaliar_rodada(por_id, None, 2, False)
    assert av["status"] == "parcial", "bytes-divergentes tem que derrubar 'completo'"
    assert av["rt_q"] == 1, "tem que contar junto com rt-quebrado, que e' o retorno fail-closed"


def test_compare_recua_para_dados_quando_a_cauda_nao_bate():
    """A cauda carrega campos que so' existem na rota TCF (knobs, granularidade, accel), e
    nenhuma referencia da stdlib os tem. Sem cauda identica, pareia por fonte/forma/escala/
    compressao. O estrito vem primeiro: o recuo so' cobre quem ficaria sem veredito."""
    caso = "tcf-flat|synth|flat-mixed|base|layer|serial+t1|min_len=3|none|cython"
    ref = "json-ref-str|synth|flat-mixed|base|call|serial+t1|-|none|cython"

    def corpo(d: Path):
        a = _escreve(d, "a", [_rec(caso, 1000), _rec(ref, 100)], _run())
        b = _escreve(d, "b", [_rec(caso, 1200), _rec(ref, 100)], _run())
        r = CMP.comparar(a, b)
        assert r["contagem"]["sem-referencia"] == 0, "o recuo tem que dar veredito"
        assert r["contagem"]["PIOR"] == 1
        assert r["pareamento_por_dados"] == 1
        linha = next(ln for ln in r["linhas"] if ln["case_id"] == caso)
        assert linha["pareamento"] == "dados" and linha["delta_pct"] == 20.0
    _com_tmp(corpo)


def test_compare_estrito_tem_precedencia_sobre_o_recuo():
    """Havendo cauda identica, o veredito sai dela e nada muda em relacao ao que ja' existia."""
    caso = "tcf-flat|synth|flat-mixed|base|call|serial+t1|-|none|cython"
    estrita = "csv-ref|synth|flat-mixed|base|call|serial+t1|-|none|cython"
    larga = "json-ref-str|synth|flat-mixed|base|layer|serial+t1|-|none|cython"

    def corpo(d: Path):
        # a referencia LARGA dobra de tempo; se ela entrasse na conta, o veredito mudaria
        a = _escreve(d, "a", [_rec(caso, 1000), _rec(estrita, 100), _rec(larga, 100)], _run())
        b = _escreve(d, "b", [_rec(caso, 1000), _rec(estrita, 100), _rec(larga, 200)], _run())
        r = CMP.comparar(a, b)
        linha = next(ln for ln in r["linhas"] if ln["case_id"] == caso)
        assert linha["pareamento"] == "cauda"
        assert r["pareamento_por_dados"] == 0
        assert linha["verdict"] == "IGUAL" and linha["pares_referencia"] == 1
    _com_tmp(corpo)


def _distancias_ate_a_referencia(ordem):
    """Para cada celula de DADO, quantas posicoes ate' a referencia que vai parea-la."""
    pos = {c["case_id"]: i for i, c in enumerate(ordem)}
    envelope = {"sentinela", "sondas"}

    def eh_ref(c):
        return CMP._caminho(c["case_id"]) in CMP.REFERENCIAS

    def chave(c):
        return CMP._chave_de_dado(c["case_id"], {"vectors": c["vectors"], "fonte": c["fonte"]})

    por_cauda, por_dado = {}, {}
    for c in ordem:
        if eh_ref(c):
            por_cauda.setdefault(c["case_id"].split("|", 1)[1], []).append(c["case_id"])
            por_dado.setdefault(chave(c), []).append(c["case_id"])
    fora = []
    for c in ordem:
        if eh_ref(c) or c["fonte"] in envelope or c["fonte"].startswith("pin-"):
            continue
        cands = por_cauda.get(c["case_id"].split("|", 1)[1]) or por_dado.get(chave(c)) or []
        if cands:
            fora.append(min(abs(pos[c["case_id"]] - pos[r]) for r in cands))
    return fora


def test_ordem_poe_a_referencia_ao_lado_do_caso():
    """A razao caso/referencia so' cancela a maquina se os dois forem medidos perto no tempo.

    Na ordem do arquivo a referencia ficava a 17 posicoes de mediana, e a deriva entre elas
    entrava inteira na razao (lab 2026-09-21-0300). O teste fixa o ganho: sem a ordenacao a
    mediana passa de 5; com ela, fica em 1 e nenhum caso passa de 20 posicoes."""
    sel = PL.selecionar(PL.carregar("nucleo"), CASES)
    antes = _distancias_ate_a_referencia(sel)
    depois = _distancias_ate_a_referencia(ordenar_vizinho(list(sel)))
    assert antes and depois and len(antes) == len(depois)
    import statistics as _st
    assert _st.median(antes) > 5, f"o problema que a ordem resolve sumiu: mediana {_st.median(antes)}"
    assert _st.median(depois) <= 1, f"mediana depois da ordem: {_st.median(depois)}"
    assert max(depois) <= 20, f"pior caso depois da ordem: {max(depois)}"


def test_ordem_e_deterministica_e_nao_perde_caso():
    """Ordem de rodada e' parte da reprodutibilidade: mesma entrada, mesma saida, mesmo conjunto."""
    sel = PL.selecionar(PL.carregar("nucleo"), CASES)
    a = [c["case_id"] for c in ordenar_vizinho(list(sel))]
    b = [c["case_id"] for c in ordenar_vizinho(list(sel))]
    assert a == b, "a ordenacao tem que ser deterministica"
    assert sorted(a) == sorted(c["case_id"] for c in sel), "nao pode tirar nem duplicar caso"
    # e ela tem que ser estavel: reordenar a entrada nao pode mudar o AGRUPAMENTO
    invertida = [c["case_id"] for c in ordenar_vizinho(list(reversed(list(sel))))]
    assert sorted(invertida) == sorted(a)


def test_matriz_tem_celula_no_regime_alvo():
    """O regime alvo declarado no ticket e' payload de API. A matriz parava em R=100."""
    escalas = {c["vectors"]["escala"].get("R") for c in CASES}
    assert min(escalas) <= 20, f"menor R da matriz: {min(escalas)}"
    alvo = [c["case_id"] for c in CASES if c["vectors"]["escala"].get("R") == 20]
    caminhos = {cid.split("|", 1)[0] for cid in alvo}
    assert "tcf-flat" in caminhos and "tcf-8h" in caminhos, caminhos
    assert any("-ref" in c for c in caminhos), "sem referencia, a celula nao vira veredito"
    # e a referencia tem que parear pela cauda ESTRITA, nao pelo recuo
    ids = {c["case_id"] for c in CASES}
    for cid in alvo:
        if "-ref" in cid.split("|", 1)[0]:
            continue
        cauda = cid.split("|", 1)[1]
        assert any(f"{r}|{cauda}" in ids for r in CMP.REFERENCIAS), cid


def test_compare_referencia_limiar_respeita_o_ruido_do_candidato():
    """Candidato com piso de ruido de 10%: +8% na razao e' ruido, nao regressao."""
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("tcf-flat|x", 1000), _rec("csv-ref|x", 100)], _run())
        b = _escreve(d, "b", [_rec("tcf-flat|x", 1080), _rec("csv-ref|x", 100)], _run(piso=0.10))
        r = CMP.comparar(a, b)
        assert r["contagem"]["PIOR"] == 0 and r["contagem"]["RUIDO"] == 1
    _com_tmp(corpo)


def test_compare_rodada_sem_referencia_usa_calibrador():
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("k1", 1000)], _run())
        b = _escreve(d, "b", [_rec("k1", 1200)], _run())
        r = CMP.comparar(a, b)
        assert r["normalizacao"] == "calibrador" and r["contagem"]["PIOR"] == 1
    _com_tmp(corpo)


def test_compare_expoe_a_adjudicacao_da_rodada():
    """A adjudicacao vem do run.json e o comparador a entrega; o termico segue so' aviso."""
    def corpo(d: Path):
        a = _escreve(d, "a", [_rec("k1", 1000)], _run(nota="aceita first-order"))
        b = _escreve(d, "b", [_rec("k1", 1000)], _run())
        r = CMP.comparar(a, b)
        assert r["adjudicacao"]["baseline"] == "aceita first-order"
        assert r["adjudicacao"]["candidato"] is None
    _com_tmp(corpo)


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
