"""Testes da view lazy/consultável sobre blob TCF.

Promovida pro core em `tcf.view` (A4, plano 0.8): camada read-only que lê
#TCF.8M (legado cortado, ADR-0032), não muda encode/decode/formato. Shim de
compat em scripts/tcf_lazy/.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tcf import encode, decode, view, SPEC_CNPJ   # noqa: E402  (caminho canônico A4)
from tcf.natures import SPEC_DATA_ISO   # noqa: E402


# ---- #TCF.8 self-describing: natures (revertidas lazy) + colunas anonimas ----

def test_lazy_tcf8_nature_reverte():
    table = {"doc": ["11.222.333/0001-81", "11.222.333/0001-81"], "x": ["a", "b"]}
    blob = encode(table, schema={"doc": SPEC_CNPJ})
    assert blob.startswith("#TCF.8M")              # familia self-describing
    v = view(blob)
    assert v.columns == ["doc", "x"]
    # coluna com nature volta REVERTIDA (decode_value lazy no _col)
    assert v.select(["doc"])[0]["doc"] == "11.222.333/0001-81"
    assert v.where("doc", "11.222.333/0001-81").count() == 2


def test_lazy_tcf8_nature_em_modo_dict_reverte_no_where_e_group():
    """REGRESSAO: a reversao da nature existia SO' no `_col`; o caminho L4
    (`_dict_parts` -> where/group_count) comparava contra o PAYLOAD cru.

    Medido no bug: nesta coluna `where('dt','2025-01-01')` devolvia 0 (verdade: 8) e
    `group_count` devolvia chaves ordinais ('739252') — errado e SEM erro. O `_col` e o
    `decode()` estavam certos, o que escondia a divergencia. Fonte unica agora:
    `LazyTCF._reverte_nature`, usada pelos DOIS caminhos.

    O regime importa: a nature so' vence o FLOOR em modo dict com k moderado — k=50/n=400
    emite `#TCF.8M@...=dt:dt,@v` (re-pin 2026-08-13, weld A ADR-0041: o `:id` e' o
    wire_id `dt`; a coluna por acaso tambem se chama `dt`). Com k pequeno o dict sem
    nature ganha e a coluna nem carrega `:id`, que era por que o bug passava despercebido.
    """
    import datetime as _dt
    base = _dt.date(2025, 1, 1)
    datas = [(base + _dt.timedelta(days=i % 50)).isoformat() for i in range(400)]
    outra = [str(i % 7) for i in range(400)]
    blob = encode({"dt": datas, "v": outra}, schema={"dt": SPEC_DATA_ISO})
    cabecalho = blob.splitlines()[0]
    assert "dt:dt" in cabecalho, "o regime mudou: a nature nao venceu em dict"
    assert "@" in cabecalho, "o regime mudou: a coluna nao esta' em modo dict"

    v = view(blob)
    # where L4 (varre o stream de indices, compara nos K unicos) tem de ver o VALOR
    assert v.where("dt", "2025-01-01").count() == datas.count("2025-01-01")
    # group_count (L3, estrutural) tem de agrupar por VALOR, nao por payload
    chaves = list(view(blob).group_count("dt"))
    assert all(c.startswith("2025-") for c in chaves), f"chaves nao revertidas: {chaves[:3]}"
    # predicado e cruzamento de coluna seguem coerentes
    fev = view(blob).where("dt", pred=lambda d: d[5:7] == "02")
    assert fev.count() == sum(1 for d in datas if d[5:7] == "02")
    # e o caminho materializado continua certo (nao regrediu)
    assert view(blob)._col("dt")[:2] == datas[:2]
    assert decode(blob)["dt"][:2] == datas[:2]


def test_lazy_tcf8_anonima_posicional():
    blob = encode({"aa": ["x", "y"], "bb": ["p", "q"]}, drop_names=True)
    v = view(blob)
    assert v.columns == ["0", "1"]                 # nome = ordem
    assert v.select(["0"]) == [{"0": "x"}, {"0": "y"}]


def test_lazy_tcf8_laziness_preservada():
    table = {"doc": ["11.222.333/0001-81", "11.222.333/0001-81"],
             "x": ["a", "b"], "y": ["c", "d"]}
    blob = encode(table, schema={"doc": SPEC_CNPJ})
    v = view(blob)
    v.select(["x"])                                # so' toca x
    assert v.touched == ["x"]                      # doc/y nao materializados


def test_a4_shim_backcompat():
    """O caminho antigo `from tcf_lazy import view` re-exporta o mesmo objeto de tcf.view."""
    import tcf as _tcf
    from tcf_lazy import view as shim_view
    from tcf_lazy import LazyTCF as shim_LazyTCF
    assert shim_view is _tcf.view
    assert shim_LazyTCF is _tcf.LazyTCF


TABLE = {
    "cliente": ["Ana", "Bruno", "Carla", "Diego", "Ana", "Bruno"],
    "cidade":  ["Sao Paulo", "Sao Paulo", "Rio de Janeiro",
                "Sao Paulo", "Rio de Janeiro", "Sao Paulo"],
    "plano":   ["Premium", "Basic", "Premium", "Premium", "Basic", "Premium"],
    "valor":   ["120", "80", "200", "120", "80", "150"],
}


@pytest.fixture
def blob():
    return encode(TABLE)


def test_columns_e_nrows(blob):
    v = view(blob)
    assert v.columns == list(TABLE)
    assert v.nrows == 6


def test_count_total(blob):
    assert view(blob).count() == 6


def test_agregadores_globais(blob):
    v = view(blob)
    assert v.sum("valor") == 750.0
    assert v.min("valor") == 80.0
    assert v.max("valor") == 200.0
    assert v.avg("valor") == 125.0


def test_filtro_mais_agregacao(blob):
    v = view(blob)
    f = v.where("cidade", "Sao Paulo")
    assert f.count() == 4
    assert f.sum("valor") == 470.0          # 120+80+120+150
    assert f.avg("valor") == 117.5


def test_alinhamento_de_linha(blob):
    # where em cidade -> índices; select traz a MESMA linha em outra coluna
    rows = view(blob).where("cidade", "Rio de Janeiro").select(["cliente", "valor"])
    assert rows == [{"cliente": "Carla", "valor": "200"},
                    {"cliente": "Ana", "valor": "80"}]


def test_filtro_encadeado_and(blob):
    f = view(blob).where("cidade", "Sao Paulo").where("plano", "Premium")
    assert f.count() == 3                    # Ana, Diego, Bruno(150)
    assert f.sum("valor") == 390.0           # 120+120+150


def test_filtro_por_predicado(blob):
    f = view(blob).where("valor", pred=lambda x: int(x) >= 120)
    assert sorted(f.indices) == [0, 2, 3, 5]
    assert f.count() == 4


def test_seletividade_count_nao_materializa(blob):
    """`count()` responde pela ESTRUTURA, sem construir valor nenhum.

    Re-pin de 2026-08-24. Antes este teste afirmava `len(touched) == 1`, porque o
    caminho do `nrows` marcava a coluna como tocada ao contar os `\\n` do corpo raw.
    Contar separadores não materializa valor, e `touched` alimenta
    `materialized_bytes`: o efeito era um `count()` puro reportar 94,1% de
    materialização com o cache vazio, ou seja, o relatório que existe para medir a
    laziness mentia sobre ela. A afirmação nova é mais forte que a antiga.
    """
    v = view(blob)
    assert v.count() == 6
    rep = v.report()
    assert rep["touched"] == []
    assert rep["materialized_bytes"] == 0
    assert rep["pct"] == 0.0
    assert rep["n_cols"] == 4
    assert v._cache == {}                    # nenhuma coluna virou lista de valores


def test_seletividade_filtro_agrega_duas(blob):
    v = view(blob)
    v.where("cidade", "Sao Paulo").sum("valor")
    rep = v.report()
    assert set(rep["touched"]) == {"cidade", "valor"}   # nunca tocou cliente/plano
    assert rep["materialized_bytes"] < rep["total_bytes"]


def test_correto_vs_decode_completo(blob):
    # a soma via lazy bate com a soma via decode() completo
    full = decode(blob)
    esperado = sum(float(x) for x in full["valor"])
    assert view(blob).sum("valor") == esperado


def test_nao_numerico_erra(blob):
    with pytest.raises(ValueError):
        view(blob).sum("cliente")            # "Ana" não é número


def test_vazios_sao_ignorados():
    t = {"id": ["1", "2", "3"], "v": ["10", "", "30"]}
    v = view(encode(t))
    assert v.sum("v") == 40.0                 # ignora o vazio
    assert v.avg("v") == 20.0                 # média sobre 2 valores


def test_coluna_inexistente(blob):
    with pytest.raises(KeyError):
        view(blob).sum("inexistente")


# --- L3: contar/agrupar sem expandir (via dict/raw) ---

def test_tem_coluna_dict(blob):
    # garante que o caminho estrutural (dicionario @) e' exercido neste fixture
    assert "dict" in view(blob)._mode.values()


def test_nrows_estrutural(blob):
    assert view(blob).nrows == 6


def test_group_count_cidade(blob):
    assert view(blob).group_count("cidade") == {"Sao Paulo": 4, "Rio de Janeiro": 2}


def test_group_count_correto_vs_decode(blob):
    full = decode(blob)
    for c in view(blob).columns:
        assert view(blob).group_count(c) == dict(Counter(full[c]))


# --- L4: filtro pelo índice do dicionário (sem decodar tudo) ---

def test_where_dict_equivale_a_decode(blob):
    full = decode(blob)
    esperado = [i for i, c in enumerate(full["cidade"]) if c == "Sao Paulo"]
    assert view(blob).where("cidade", "Sao Paulo").indices == esperado


def test_where_dict_nao_materializa_a_coluna(blob):
    v = view(blob)
    assert v._mode["cidade"] == "dict"          # garante o caminho L4
    v.where("cidade", "Sao Paulo")
    assert "cidade" not in v._cache             # não construiu a lista de N valores


def test_where_valor_inexistente(blob):
    assert view(blob).where("cidade", "Berlin").count() == 0


def test_where_dict_predicado(blob):
    f = view(blob).where("plano", pred=lambda x: x == "Premium")
    assert f.count() == 4


def test_where_encadeado_dict_via_stream(blob):
    # cidade e plano são dict -> AND lê só posições no stream; resultado bate com decode
    full = decode(blob)
    esperado = [i for i in range(len(full["cidade"]))
                if full["cidade"][i] == "Sao Paulo" and full["plano"][i] == "Premium"]
    got = view(blob).where("cidade", "Sao Paulo").where("plano", "Premium").indices
    assert got == esperado


# --- L5: layout p/ baixa latência (sort_by + group_ranges/agg_by) ---

@pytest.fixture
def sorted_blob():
    return encode(TABLE, sort_by="cidade")


def test_group_ranges_exige_agrupado(blob):
    with pytest.raises(ValueError):
        view(blob).group_ranges("cidade")          # blob original não está agrupado


def test_group_ranges_contiguo_cobre_tudo(sorted_blob):
    spans = sorted(view(sorted_blob).group_ranges("cidade").values())
    assert spans[0][0] == 0 and spans[-1][1] == 6
    assert all(spans[i][1] == spans[i + 1][0] for i in range(len(spans) - 1))


def test_agg_by_sum_por_grupo(sorted_blob):
    assert view(sorted_blob).agg_by("cidade", "valor", "sum") == {
        "Sao Paulo": 470.0, "Rio de Janeiro": 280.0}


def test_agg_by_count(sorted_blob):
    assert view(sorted_blob).agg_by("cidade") == {"Sao Paulo": 4, "Rio de Janeiro": 2}


def test_agg_by_vs_groupby_manual(sorted_blob):
    from collections import defaultdict
    full = decode(sorted_blob)
    man: dict = defaultdict(float)
    for c, v in zip(full["cidade"], full["valor"]):
        man[c] += float(v)
    assert view(sorted_blob).agg_by("cidade", "valor", "sum") == dict(man)


def test_report_pct_nao_passa_de_100_sem_dupla_contagem(blob):
    """A2 (achado no banco de testes A1): coluna dict tocada por _dict_parts
    (estrutural) E depois por _col (materializacao) era contada 2x em `touched`,
    fazendo materialized_bytes/pct passar de 100%. `touched` deve ser unico."""
    v = view(blob)
    v.group_count("cidade")     # _dict_parts -> touched
    v.where("cidade", "Sao Paulo")  # _dict_parts (guard)
    v.select(["cidade"])        # _col(cidade) -> nao pode re-adicionar
    assert len(v.touched) == len(set(v.touched)), f"touched tem duplicata: {v.touched}"
    rep = v.report()
    assert rep["pct"] <= 100.0, f"pct {rep['pct']}% > 100% (dupla contagem)"


def test_venda_isolada_toca_fracao(blob):
    """View fresca + 1 query so' deve tocar < 100% do blob (a 'venda')."""
    v = view(blob)
    v.where("cidade", "Sao Paulo").sum("valor")
    rep = v.report()
    assert set(v.touched) == {"cidade", "valor"}
    assert rep["pct"] < 100.0


# ---- Weld 2026-08-23 (lab reprova-where-posicional): int = POSICAO nas 3 portas ----
# A view era a unica porta publica que NAO resolvia int (ADR-0047 cobre
# encode/decode); e select(0) era engolido por truthiness (todas as colunas,
# calado) e value int no where respondia 0 calado (valores decodados sao str).

class TestColunaPosicionalNaView:
    @pytest.fixture
    def vb(self):
        return view(encode({
            "cidade": ["SP", "RJ", "SP", "BH", "SP", "RJ"],
            "qtd": ["10", "5", "10", "7", "3", "10"],
        }))

    def test_int_resolve_posicao_igual_ao_nome(self, vb):
        assert vb.where(0, "SP").count() == vb.where("cidade", "SP").count() == 3
        assert vb.sum(1) == vb.sum("qtd") == 45.0
        assert vb.group_count(0) == vb.group_count("cidade")
        assert vb.column_bytes(1) == vb.column_bytes("qtd")
        f = vb.where(0, "SP")
        assert f.where(1, "10").count() == 2          # Filtered.where idem

    def test_select_escalar_e_posicao_zero(self, vb):
        """`select(0)` era a calada real: `cols or self._order` engolia o 0 e
        devolvia TODAS as colunas. Agora escalar = sobrecarga de 1 coluna (como
        no schema=), e as chaves de saida sao sempre NOMES."""
        so_cidade = vb.select(0)
        assert so_cidade == vb.select("cidade") == vb.select(["cidade"])
        assert list(so_cidade[0]) == ["cidade"]
        assert len(so_cidade) == 6

    def test_posicao_fora_do_range_e_bool_erram(self, vb):
        with pytest.raises(ValueError, match="fora do range"):
            vb.where(9, "SP")
        with pytest.raises(TypeError, match="str \(nome\) ou int"):
            vb.where(True, "SP")
        with pytest.raises(ValueError, match="fora do range"):
            vb.where(-1, "SP")                        # sem negativo, como no schema=

    def test_value_de_outro_tipo_e_convertido(self, vb):
        """`where('qtd', 10)` numa coluna de TEXTO respondia 0 CALADO (10 != '10').
        Agora o valor e' LIDO no tipo da coluna, com aviso: modo soft (default)."""
        with pytest.warns(UserWarning, match="foi lido como"):
            assert vb.where("qtd", 10).count() == 3
        assert vb.where("qtd", "10").count() == 3     # tipo certo: sem cast, sem aviso
        assert vb.coercoes                            # a conversao fica registrada

    def test_modo_strict_exige_o_tipo_da_coluna(self, vb):
        """`.strict()` troca a conversao automatica por erro, pra codigo rigido."""
        with pytest.raises(TypeError, match="STRICT"):
            vb.strict().where("qtd", 10)
        assert vb.where("qtd", "10").count() == 3     # o tipo certo passa igual


# ---- Weld 2026-08-23: view() sobre `.8H` que e' TABELA RETANGULAR ----
# Uma coluna tipada (ou um None) tira o dict do `.8M`, e o view recusava a tabela
# inteira: `BUG-VIEW-RECUSA-COLUNA-TIPADA`. O tipo primitivo ja' e' um spec, so' que
# implicito, e ja' viaja no header; aqui o view passa a ler o que esta' declarado.

class TestViewSobreTabelaTipada:
    @pytest.fixture
    def vt(self):
        return view(encode({
            "cidade": ["SP", "SP", "RJ", "SP"],
            "valor":  [120, 80, 200, 120],
            "ativo":  [True, False, True, True],
        }))

    def test_tipo_volta_nativo(self, vt):
        linha = vt.select()[0]
        assert linha == {"cidade": "SP", "valor": 120, "ativo": True}
        assert isinstance(linha["valor"], int) and isinstance(linha["ativo"], bool)

    def test_consulta_com_valor_nativo(self, vt):
        assert vt.where("valor", 120).count() == 2
        assert vt.where("ativo", True).count() == 3
        assert vt.where("cidade", "SP").sum("valor") == 320.0

    def test_tipo_trocado_e_lido_no_tipo_da_coluna(self, vt):
        """O arquivo e' texto: `where(col, "120")` numa coluna `n` e' intencao clara.
        O valor e' convertido (1 cast, no lado barato) e a conversao fica registrada."""
        with pytest.warns(UserWarning):
            assert vt.where("valor", "120").count() == 2
        with pytest.warns(UserWarning):
            assert vt.where("cidade", 5).count() == 0      # convertido pra '5': nao ha'
        with pytest.warns(UserWarning):
            assert vt.where("ativo", 1).count() == 3       # 1 lido como True

    def test_o_que_nao_tem_leitura_possivel_erra(self, vt):
        """Converter e' ler a intencao, nao adivinhar: 'banana' nao e' bool."""
        with pytest.raises(TypeError, match="não tem leitura possível"):
            vt.where("ativo", "banana")
        with pytest.raises(TypeError, match="não tem leitura possível"):
            vt.where("valor", "dez")

    def test_paridade_com_decode(self, vt):
        """O que a view serve e' o que o decode devolve, valor e TIPO."""
        blob = encode({"cidade": ["SP", "SP", "RJ", "SP"],
                       "valor": [120, 80, 200, 120],
                       "ativo": [True, False, True, True]})
        esperado = decode(blob)
        servido = {c: [linha[c] for linha in vt.select()] for c in vt.columns}
        assert servido == esperado

    def test_laziness_preservada(self, vt):
        """A razao de ser do view: a pergunta materializa uma FRACAO do blob."""
        vt.where("cidade", "SP").count()
        assert vt.touched == ["cidade"]              # `valor`/`ativo` nem decodaram
        assert vt.materialized_bytes < vt.total_bytes

    def test_null_em_coluna_de_texto(self):
        """Um `None` tambem tirava a tabela do `.8M`, sem tipo nenhum envolvido."""
        v = view(encode({"a": ["x", None, "z"], "b": ["1", "2", "3"]}))
        assert v.select() == [{"a": "x", "b": "1"}, {"a": None, "b": "2"},
                              {"a": "z", "b": "3"}]

    def test_dataset_de_registros(self):
        """A outra forma retangular: `encode(list[dict])`."""
        v = view(encode([{"n": "ana", "v": 1}, {"n": "bob", "v": 2}]))
        assert v.columns == ["n", "v"]
        assert v.where("v", 2).select() == [{"n": "bob", "v": 2}]

    @pytest.mark.parametrize("dado,trecho", [
        ([{"a": {"b": 1}}],           "retangular"),   # aninhado
        ([{"a": 1}, {"b": 2}],        "retangular"),   # ragged: campo opcional
        (42,                          "TABELA"),       # escalar solto na raiz
    ])
    def test_o_que_nao_e_tabela_erra_com_dica(self, dado, trecho):
        with pytest.raises(ValueError, match=trecho):
            view(encode(dado))

    def test_single_col_tambem_e_consultavel(self):
        """Uma coluna so' tambem e' tabela: o view recusava `[1,2,3]` E `['1','2','3']`,
        sem razao. `sum` responde igual nos dois; cada um devolve o SEU tipo."""
        vi, vs = view(encode([1, 2, 3])), view(encode(["1", "2", "3"]))
        assert vi.sum(0) == vs.sum(0) == 6.0
        assert vi.count() == vs.count() == 3
        assert vi.select() == [{"0": 1}, {"0": 2}, {"0": 3}]      # int
        assert vs.select() == [{"0": "1"}, {"0": "2"}, {"0": "3"}]  # str
        assert view(encode([True, False])).where(0, True).count() == 1


class TestAgregadorPorTipo:
    """O `sum` responde nos dois tipos, e se comporta como o Python faria."""

    @pytest.mark.parametrize("dado,esperado", [
        ([1, 2, 3],            6.0),   # numero na fonte: garantido
        (["1", "2", "3"],      6.0),   # texto numerico: converte, como float("1")
        ([1.5, 2.5],           4.0),
        ([True, False, True],  2.0),   # bool soma como no Python
        ([1, None, 3],         4.0),   # nulo NAO entra na conta (nao e' zero)
        (["1", None, "3"],     4.0),
    ])
    def test_sum(self, dado, esperado):
        assert view(encode(dado)).sum(0) == esperado

    def test_media_ignora_nulo(self):
        """Se o nulo contasse como zero, a media de [1,None,3] daria 1.33."""
        assert view(encode([1, None, 3])).avg(0) == 2.0

    def test_nao_numerico_erra_como_python(self):
        with pytest.raises(ValueError, match="could not convert"):
            view(encode(["a", "b"])).sum(0)


class TestMultiColTipada:
    """Tabela com uma coluna de texto e uma numerica: a consulta inteira, nos 2 tipos."""

    @pytest.fixture(params=["tipado", "texto"])
    def v(self, request):
        valores = [10, 20, 30, 40, 50]
        if request.param == "texto":
            valores = [str(x) for x in valores]
        return view(encode({"cidade": ["SP", "RJ", "SP", "MG", "SP"],
                            "valor": valores}))

    def test_agregadores(self, v):
        assert v.count() == 5
        assert v.sum("valor") == 150.0
        assert v.avg("valor") == 30.0
        assert (v.min("valor"), v.max("valor")) == (10.0, 50.0)

    def test_grupo(self, v):
        assert v.group_count("cidade") == {"SP": 3, "RJ": 1, "MG": 1}
        assert v.group_sum("cidade", "valor") == {"SP": 90.0, "RJ": 20.0, "MG": 40.0}

    def test_filtro(self, v):
        f = v.where("cidade", "SP")
        assert f.count() == 3
        assert f.sum("valor") == 90.0
        assert [linha["cidade"] for linha in f.select()] == ["SP", "SP", "SP"]

    def test_group_sum_com_nulo(self):
        """Nulo fora da soma, mas o grupo existe: `B` soma 0.0, nao some."""
        v = view(encode({"c": ["A", "B", "A"], "n": [10, None, 5]}))
        assert v.group_sum("c", "n") == {"A": 15.0, "B": 0.0}

    def test_group_sum_toca_so_as_duas_colunas(self):
        v = view(encode({"c": ["A", "B", "A"], "n": [1, 2, 3],
                         "obs": ["x" * 50, "y" * 50, "z" * 50]}))
        v.group_sum("c", "n")
        assert sorted(v.touched) == ["c", "n"]        # `obs` nem decodou


class TestCaminhoRapidoConcordaComOLento:
    """O filtro por dicionario (`@`) compara os K UNICOS; o comum decoda as N linhas.

    Latente: os unicos saem do dicionario em TEXTO, e o caminho rapido comparava
    sem reverter o tipo. `where("ativo", True)` respondia ZERO numa coluna booleana
    em modo `@`, porque comparava `True` com `"true"`, e o `group_count` devolvia a
    chave `'true'` em vez de `True`. Os dois caminhos discordavam conforme o modo
    da coluna, que o usuario nem escolhe.
    """

    @pytest.fixture
    def tabela(self):
        n = 600      # grande o bastante pra coluna low-card virar `@dict`
        return {"b": [i % 3 == 0 for i in range(n)],
                "c": [f"c{i % 7}" for i in range(n)],
                "n": [i % 5 for i in range(n)]}

    def test_where_bool_no_modo_dict(self, tabela):
        v = view(encode(tabela))
        assert v._mode["b"] == "dict"                  # o caminho rapido esta' ativo
        esperado = sum(1 for x in tabela["b"] if x)
        assert v.where("b", True).count() == esperado
        assert v.where("b", False).count() == len(tabela["b"]) - esperado

    def test_where_int_no_modo_dict(self, tabela):
        v = view(encode(tabela))
        assert v.where("n", 3).count() == sum(1 for x in tabela["n"] if x == 3)

    def test_group_count_devolve_tipo_nativo(self, tabela):
        from collections import Counter
        v = view(encode(tabela))
        assert v.group_count("b") == dict(Counter(tabela["b"]))     # True/False, nao 'true'
        assert v.group_count("n") == dict(Counter(tabela["n"]))

    def test_grupo_bate_com_select(self, tabela):
        """A chave do grupo tem que ser a MESMA coisa que o `select` devolve."""
        v = view(encode(tabela))
        do_select = {linha["b"] for linha in v.select(["b"])}
        assert set(v.group_count("b")) == do_select


class TestContratoSoftEStrict:
    """O arquivo e' texto, entao o tipo e' leitura: `where` LE o valor no tipo da
    coluna (soft, default) e `.strict()` exige o tipo exato (higiene de codigo).

    Mercado, pra referencia: Polars e DuckDB erram por padrao (DuckDB apertou na
    0.10, removendo o cast implicito pra VARCHAR); pandas converte calado e e'
    citado como armadilha. Aqui o rigor existe, mas e' opt-in.
    """

    @pytest.fixture
    def hard(self):
        return view(encode({"b": [True, False, True], "n": [1, 2, 3]}))

    @pytest.fixture
    def soft(self):
        return view(encode({"b": ["true", "false", "true"], "n": ["1", "2", "3"]}))

    def test_le_nos_dois_sentidos(self, hard, soft):
        with pytest.warns(UserWarning):
            assert hard.where("b", "true").count() == 2      # texto -> bool
        with pytest.warns(UserWarning):
            assert hard.where("n", "1").count() == 1         # texto -> numero
        with pytest.warns(UserWarning):
            assert soft.where("b", True).count() == 2        # bool -> texto
        with pytest.warns(UserWarning):
            assert soft.where("n", 1).count() == 1           # numero -> texto

    def test_tipo_certo_nao_avisa_nem_converte(self, hard):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error")                   # qualquer aviso falha
            assert hard.where("b", True).count() == 2
            assert hard.where("n", 1).count() == 1
        assert hard.coercoes == []

    def test_cast_e_do_lado_barato(self):
        """Converte UM valor, nunca as N linhas: o custo nao cresce com a tabela."""
        import importlib
        # `import tcf.view as mod` pega a FUNCAO `view` (o __init__ reexporta ela
        # com o mesmo nome do modulo), nao o modulo.
        mod = importlib.import_module("tcf.view")
        orig, chamadas = mod._converte, []
        mod._converte = lambda v, s: (chamadas.append(1), orig(v, s))[1]
        try:
            v = view(encode({"b": [i % 3 == 0 for i in range(5000)]}))
            with pytest.warns(UserWarning):
                v.where("b", "true").count()
            assert len(chamadas) == 1                        # 1 cast, 5000 linhas
        finally:
            mod._converte = orig

    @pytest.mark.parametrize("grafia,esperado", [
        ("true", True), ("TRUE", True), ("1", True), ("yes", True), ("sim", True),
        ("false", False), ("0", False), ("no", False), (" True ", True),
    ])
    def test_grafias_de_bool(self, hard, grafia, esperado):
        """Lista FECHADA, como o PostgreSQL. String nao-vazia virar True por
        truthiness e' a armadilha do pandas, e nao acontece aqui."""
        with pytest.warns(UserWarning):
            n = hard.where("b", grafia).count()
        assert n == (2 if esperado else 1)

    def test_nao_adivinha(self, hard):
        for lixo in ("banana", "sim/nao"):
            with pytest.raises(TypeError, match="não tem leitura possível"):
                hard.where("b", lixo)

    def test_strict_e_opt_in_e_encadeavel(self, hard):
        assert hard.strict() is hard                          # devolve a propria view
        with pytest.raises(TypeError, match="STRICT"):
            hard.where("b", "true")
        assert hard.where("b", True).count() == 2             # tipo certo passa igual

    def test_telemetria_registra_o_que_converteu(self, hard):
        with pytest.warns(UserWarning):
            hard.where("b", "true").count()
        assert len(hard.coercoes) == 1
        assert "foi lido como True" in hard.coercoes[0]


class TestCountSemMaterializar:
    """`count()` responde pela ESTRUTURA, em toda rota.

    Contar linhas nunca precisa dos valores. O dispatch escolhe, por modo de coluna,
    entre o `n` DECLARADO no cabeçalho das rotas densas, os contadores SOMADOS do
    corpo core, os SEPARADORES do corpo raw e a forma do stream no dicionário.

    Escolher a leitura errada não levanta: devolve um número errado. Por isso todo
    caso aqui confere contra `decode()`, que é a verdade.

    Levantamento e casos mínimos anotados:
    `experiments/lab/dirty/2026-08/2026-08-24/2026-08-24-0600-count-minimo/`.
    """

    @pytest.mark.parametrize("rotulo,dado", [
        ("core-texto", ["ab", "cd", "ef"]),
        ("core-rle", ["SP"] * 3),
        ("core-sequencia", [1, 2, 3]),
        ("bn-dominio", ["SP", "RJ"] * 3),
        ("bool-denso", [True, False, True]),
        ("uma-linha", ["so-uma"]),
        ("com-nulo", ["a", None, "c"]),
        ("com-vazio", ["a", "", "c"]),
        ("so-vazios", ["", "", ""]),
        ("unicode", ["São", "Ceará", "日本"]),
        ("separador-no-valor", ["a,b", "c=d", "e:f"]),
        ("alta-cardinalidade", [f"{i}-{i * 7919}" for i in range(6)]),
        ("float", [1.5, 2.25, -0.75]),
        ("K-na-fronteira-94", [f"v{i % 94}" for i in range(200)]),
        ("K-na-fronteira-95", [f"v{i % 95}" for i in range(200)]),
    ])
    def test_single_col_bate_com_decode(self, rotulo, dado):
        blob = encode(dado)
        assert view(blob).count() == len(decode(blob))

    def test_single_col_nao_decodifica_na_abertura(self):
        """Abrir uma view não pode custar o decode do blob.

        Regressão de 2026-08-24: o ramo single-col chamava `decode()` no `__init__` e
        guardava a lista no cache, então `view(blob)` já materializava 100% do wire
        antes de qualquer pergunta. O comentário no código chegava a justificar isso
        com "não há laziness a preservar", o que é falso: o blob ser a coluna não
        obriga a lê-lo antes de perguntarem.
        """
        v = view(encode([f"v{i % 5}" for i in range(500)]))
        assert v._cache == {}
        assert v.touched == []
        assert v.count() == 500
        assert v._cache == {}                 # nem o count materializou
        assert v.select(0)                    # aqui sim, e só aqui
        assert v._cache != {}

    def test_tipo_vem_do_header_sem_decodificar(self):
        """A tag de tipo está no char de índice 6, e ler dali é de graça."""
        for dado, esperado in ((["ab"], "s"), ([1, 2], "n"), ([True, False], "b")):
            v = view(encode(dado))
            assert v._stype["0"] == esperado
            assert v._cache == {}             # o tipo não custou o corpo

    def test_count_nao_marca_materializacao(self):
        """`touched`/`materialized_bytes` medem o que virou VALOR, não o que foi lido."""
        blob = encode({"uf": ["SP", "RJ"] * 50, "livre": [str(i) for i in range(100)]})
        v = view(blob)
        assert v.count() == 100
        assert v.report()["materialized_bytes"] == 0
        assert v.report()["pct"] == 0.0

    @pytest.mark.parametrize("tab", [
        {"uf": ["SP", "RJ"] * 4, "n": [1, 2] * 4},                 # dict + raw
        {"a": ["p", "q", "r"], "b": ["x", "y", "z"]},              # raw
        {"c": ["Z"] * 20, "s": list(range(20)),
         "b": [i % 3 == 0 for i in range(20)]},                    # core + bool
    ])
    def test_multi_col_bate_com_decode(self, tab):
        blob = encode(tab)
        esperado = len(next(iter(decode(blob).values())))
        assert view(blob).count() == esperado

    def test_count_filtrado_bate_com_a_lista(self):
        """`where(...).count()` conta as linhas que casaram, não as que existem."""
        tab = {"uf": [["SP", "RJ", "MG"][i % 3] for i in range(90)],
               "v": list(range(90))}
        v = view(encode(tab))
        assert v.where("uf", "SP").count() == 30
        assert v.where("uf", "SP").where("v", pred=lambda x: x < 45).count() == 15
        assert v.where("uf", "ZZ").count() == 0

    def test_contador_aninhado_nao_conta_pela_metade(self):
        """`*N+d|*M|` vale N*M. Tratá-lo como N é o único erro que o SOMADO comete.

        Sem um caso que produza o aninhamento, o atalho passaria no resto da suíte e
        erraria por um fator em produção.
        """
        for dado in ([i // 4 for i in range(400)],           # patamares repetidos
                     [i % 7 for i in range(700)],            # ciclo curto
                     sorted([i % 20 for i in range(600)])):  # blocos ordenados
            blob = encode(dado)
            assert view(blob).count() == len(decode(blob)), blob[:40]


import datetime as _dt  # noqa: E402

_BASE = _dt.date(2025, 1, 1)
_TS = _dt.datetime(2025, 1, 1)
_CASOS_MULTI_DELTA = [
    ("data-iso-diaria",
     [(_BASE + _dt.timedelta(days=i)).isoformat() for i in range(1000)]),
    ("data-iso-salteada",
     [(_BASE + _dt.timedelta(days=i * 3)).isoformat() for i in range(500)]),
    ("data-iso-repetida",
     [(_BASE + _dt.timedelta(days=i // 5)).isoformat() for i in range(500)]),
    ("timestamp-horario",
     [(_TS + _dt.timedelta(hours=i)).isoformat() for i in range(500)]),
    ("timestamp-minuto",
     [(_TS + _dt.timedelta(minutes=i)).isoformat() for i in range(300)]),
]


class TestContadorMultiDelta:
    r"""REGRESSÃO: o contador multi-delta `*29+0,1|` truncava a tabela em silêncio.

    O weld do count nasceu com um regex próprio (`^\*(\d+)([+~]\d+)?\|`) que casa o
    delta único mas **não** casa o multi-delta, que o encoder emite em qualquer coluna
    de data ou datetime. Sequência de inteiros não dispara esse marcador, e a
    diversidade da primeira rodada só tinha inteiros: por isso passou.

    O dano não era só um número errado. `select()` itera `range(self.nrows)`, então a
    tabela voltava com 63 das 1000 linhas, **sem erro nenhum**.

    A correção é fonte única: quem lê o contador agora é `_contador_declarado`, de
    `composicional/hcc_seqrle.py`, que lê os dígitos até o `|` e portanto vale para
    toda grafia do marcador. Duas grafias do mesmo marcador com dois leitores era a
    causa raiz, e é a classe de bug que o T-CODE-CORE-CONSOLIDATE registra.
    """

    @pytest.mark.parametrize("rotulo,dado", _CASOS_MULTI_DELTA)
    def test_conta_e_nao_trunca(self, rotulo, dado):
        blob = encode({"c": dado})
        v = view(blob)
        assert v.count() == len(dado), f"{rotulo}: count truncou"
        assert v.nrows == len(dado), f"{rotulo}: nrows truncou"
        # o que de fato dói: a tabela voltando incompleta e sem erro
        assert len(view(blob).select()) == len(dado), f"{rotulo}: select truncou"
        assert view(blob).select("c")[-1]["c"] == dado[-1], "última linha perdida"

    def test_single_col_tambem(self):
        import datetime as dt
        dado = [(dt.date(2025, 1, 1) + dt.timedelta(days=i)).isoformat()
                for i in range(1000)]
        blob = encode(dado)
        assert view(blob).count() == len(decode(blob))

    def test_leitor_e_o_canonico(self):
        """Não reimplementar o leitor: usar o que já existe evita a divergência."""
        from tcf.composicional.hcc_seqrle import _contador_declarado
        assert _contador_declarado("*29+0,1|x") == 29     # multi-delta
        assert _contador_declarado("*7+1|v") == 7         # delta único
        assert _contador_declarado("*3|SP") == 3          # RLE simples
        assert _contador_declarado("*12~5,2|x") == 12     # periódico
        assert _contador_declarado("valor comum") == 0    # não é marcador


class TestWhereCurtoCircuitoDominio:
    """A tabela de únicos do `@dict` responde os dois extremos sem varrer o stream.

    O corpo `@` guarda os K valores distintos e um stream de N índices. A tabela é a
    lista FECHADA do que a coluna contém, então:

    - nenhum único casou: nenhuma linha pode casar, porque toda linha aponta para
      algum único. Resposta `[]`, sem ler o stream.
    - todos casaram: toda linha casa. Resposta `range(len(stream) // width)`.

    Antes os dois extremos varriam o stream inteiro decodificando índice por índice
    para chegar na mesma resposta. Medido: filtrar por valor inexistente numa coluna
    de 2000 linhas visitava 2000 posições para devolver lista vazia.

    Errar aqui não levanta, devolve o conjunto errado de linhas, então cada caso
    confere os ÍNDICES um a um contra a lista decodificada, não só a contagem.
    Diversidade completa (1358 filtros, 5 modos):
    `experiments/lab/dirty/2026-08/2026-08-24/2026-08-24-0700-where-minimo/`.
    """

    @pytest.fixture
    def tab(self):
        n = 300
        return {"c": [["SP", "RJ", "MG"][i % 3] for i in range(n)],
                "x": [str(i) for i in range(n)]}

    def test_valor_inexistente_devolve_vazio(self, tab):
        v = view(encode(tab))
        assert v._mode["c"] == "dict", "o regime mudou: a coluna não caiu em @dict"
        f = v.where("c", "ZZ")
        assert f.count() == 0
        assert f.indices == []
        assert f.select() == []

    def test_predicado_que_aceita_tudo_devolve_todas(self, tab):
        blob = encode(tab)
        v = view(blob)
        f = v.where("c", pred=lambda x: True)
        assert f.count() == 300
        assert f.indices == list(range(300))
        assert [r["c"] for r in f.select("c")] == decode(blob)["c"]

    def test_predicado_que_recusa_tudo_devolve_vazio(self, tab):
        f = view(encode(tab)).where("c", pred=lambda x: False)
        assert f.count() == 0
        assert f.indices == []

    def test_caso_do_meio_continua_varrendo_e_acertando(self, tab):
        blob = encode(tab)
        esperado = [i for i, x in enumerate(decode(blob)["c"]) if x == "SP"]
        f = view(blob).where("c", "SP")
        assert f.indices == esperado
        assert f.count() == len(esperado)

    def test_encadeado_respeita_os_extremos(self, tab):
        blob = encode(tab)
        base = view(blob).where("c", "SP")
        n = base.count()
        # nenhum único casa: o AND zera
        assert base.where("c", "ZZ").count() == 0
        # todos casam: o AND não restringe
        assert base.where("c", pred=lambda x: True).count() == n
        assert base.where("c", pred=lambda x: True).indices == base.indices

    def test_predicado_que_levanta_propaga(self, tab):
        """O atalho avalia o predicado nos K únicos, então um erro do usuário sai de
        lá e não de dentro de uma varredura de N linhas. Levantar é o certo."""
        with pytest.raises(TypeError):
            view(encode(tab)).where("c", pred=lambda x: x + 1)

    def test_valor_que_e_substring_de_outro(self):
        """Comparação é por valor, não por conteúdo de bytes: `'a'` não casa `'ab'`."""
        n = 300
        blob = encode({"c": [["a", "ab", "abc"][i % 3] for i in range(n)],
                       "x": [str(i) for i in range(n)]})
        for alvo in ("a", "ab", "abc"):
            esperado = [i for i, x in enumerate(decode(blob)["c"]) if x == alvo]
            assert view(blob).where("c", alvo).indices == esperado, alvo

    def test_coluna_de_um_unico_valor(self):
        """K=1: filtrar pelo único é o extremo 'todos casam'; por outro, o extremo vazio."""
        n = 300
        blob = encode({"c": ["SP"] * n, "x": [str(i) for i in range(n)]})
        v = view(blob)
        if v._mode["c"] != "dict":
            pytest.skip("regime: a coluna constante não caiu em @dict")
        assert v.where("c", "SP").count() == n
        assert view(blob).where("c", "RJ").count() == 0


class TestGrouping:
    """A superfície de agrupamento, fechada.

    Antes existiam só `group_count` e `group_sum`, e nenhum dos dois depois de um
    filtro: `where(...).group_count(...)`, que é o `WHERE ... GROUP BY` mais básico do
    SQL, levantava `AttributeError`.

    As decisões de semântica, que cada ferramenta resolve de um jeito, e o que o TCF
    escolheu (levantado em `experiments/lab/.../2026-08-25-0100-grouping-semantica/`):

    | questão | SQL | pandas | polars | TCF |
    |---|---|---|---|---|
    | nulo na chave forma grupo? | sim | não (`dropna=True`) | sim | **sim** |
    | grupo sem valor: `sum` | NULL | 0 | null | **0.0** |
    | ordem das chaves | indefinida | ordenada | aparição | **aparição** |
    | valor não-numérico | erro | erro/NaN | erro | **levanta** |

    Diversidade completa: 3159 agregações, 10 formas de chave × 8 de valor × 5
    tamanhos, cada uma contra a mesma conta feita em Python puro.
    """

    @pytest.fixture
    def tab(self):
        return {"uf": ["SP", "SP", "RJ", "RJ", "MG"],
                "plano": ["A", "B", "A", "B", "A"],
                "v": [10, 20, 30, 40, 50]}

    def test_as_quatro_agregacoes(self, tab):
        v = view(encode(tab))
        assert v.group_sum("uf", "v") == {"SP": 30.0, "RJ": 70.0, "MG": 50.0}
        assert view(encode(tab)).group_min("uf", "v") == {"SP": 10.0, "RJ": 30.0,
                                                          "MG": 50.0}
        assert view(encode(tab)).group_max("uf", "v") == {"SP": 20.0, "RJ": 40.0,
                                                          "MG": 50.0}
        assert view(encode(tab)).group_avg("uf", "v") == {"SP": 15.0, "RJ": 35.0,
                                                          "MG": 50.0}

    def test_group_by_duas_colunas(self, tab):
        """`GROUP BY a, b`: a chave vira a tupla dos valores."""
        assert view(encode(tab)).group_count(["uf", "plano"]) == {
            ("SP", "A"): 1, ("SP", "B"): 1, ("RJ", "A"): 1, ("RJ", "B"): 1,
            ("MG", "A"): 1}
        assert view(encode(tab)).group_sum(["uf", "plano"], "v") == {
            ("SP", "A"): 10.0, ("SP", "B"): 20.0, ("RJ", "A"): 30.0,
            ("RJ", "B"): 40.0, ("MG", "A"): 50.0}

    def test_where_mais_group_by(self, tab):
        """A combinação que faltava inteira."""
        f = view(encode(tab)).where("plano", "A")
        assert f.group_count("uf") == {"SP": 1, "RJ": 1, "MG": 1}
        assert f.group_sum("uf", "v") == {"SP": 10.0, "RJ": 30.0, "MG": 50.0}
        assert f.group_min("uf", "v") == {"SP": 10.0, "RJ": 30.0, "MG": 50.0}
        assert f.group_max("uf", "v") == {"SP": 10.0, "RJ": 30.0, "MG": 50.0}
        assert f.group_avg("uf", "v") == {"SP": 10.0, "RJ": 30.0, "MG": 50.0}

    def test_grupo_sem_valor_aproveitavel(self):
        """`sum` dá 0.0 porque o grupo existe; `min`/`max`/`avg` dão `None`.

        Sumir com o grupo esconderia que a chave estava lá. Devolver 0.0 num `min`
        seria inventar um valor que não existe na coluna.
        """
        blob = encode({"g": ["a", "a", "b", "b"], "v": [1, 2, None, None]})
        assert view(blob).group_sum("g", "v") == {"a": 3.0, "b": 0.0}
        assert view(blob).group_min("g", "v") == {"a": 1.0, "b": None}
        assert view(blob).group_max("g", "v") == {"a": 2.0, "b": None}
        assert view(blob).group_avg("g", "v") == {"a": 1.5, "b": None}
        assert view(blob).group_count("g") == {"a": 2, "b": 2}   # o grupo existe

    def test_nulo_na_chave_forma_grupo(self):
        """Como SQL, e diferente do pandas, que descarta por padrão."""
        blob = encode({"g": ["a", None, "a", "b", None], "v": [1, 2, 3, 4, 5]})
        assert view(blob).group_count("g") == {"a": 2, None: 2, "b": 1}
        assert view(blob).group_sum("g", "v") == {"a": 4.0, None: 7.0, "b": 4.0}

    def test_vazio_na_chave_e_um_grupo(self):
        blob = encode({"g": ["a", "", "a", "b", ""], "v": [1, 2, 3, 4, 5]})
        assert view(blob).group_count("g") == {"a": 2, "": 2, "b": 1}

    def test_chave_sai_no_tipo_da_coluna(self):
        blob = encode({"g": [1, 1, 2, 2], "v": [10, 20, 30, 40]})
        assert view(blob).group_sum("g", "v") == {1: 30.0, 2: 70.0}
        b2 = encode({"g": [True, False, True], "v": [1, 2, 3]})
        assert view(b2).group_count("g") == {True: 2, False: 1}

    def test_valor_nao_numerico_levanta(self):
        blob = encode({"g": ["a", "a", "b"], "v": ["1", "x", "3"]})
        for op in ("group_sum", "group_min", "group_max", "group_avg"):
            with pytest.raises(ValueError):
                getattr(view(blob), op)("g", "v")

    def test_operacao_desconhecida_diz_quais_existem(self):
        v = view(encode({"g": ["a"], "v": [1]}))
        with pytest.raises(ValueError, match="use sum, min, max ou avg"):
            v._group_agg("g", "v", "mediana")

    def test_group_by_sem_coluna_levanta(self):
        v = view(encode({"g": ["a"], "v": [1]}))
        with pytest.raises(ValueError, match="ao menos uma"):
            v.group_count([])

    def test_bate_com_a_conta_feita_na_mao(self):
        """A prova que vale: comparar com o mesmo cálculo sobre o decode."""
        import random
        r = random.Random(20260825)
        tab = {"g": [r.choice(["a", "b", "c"]) for _ in range(400)],
               "v": [r.randint(1, 100) for _ in range(400)]}
        blob = encode(tab)
        t = decode(blob)
        baldes = {}
        for k, x in zip(t["g"], t["v"]):
            baldes.setdefault(k, []).append(float(x))
        assert view(blob).group_sum("g", "v") == {k: sum(n) for k, n in baldes.items()}
        assert view(blob).group_min("g", "v") == {k: min(n) for k, n in baldes.items()}
        assert view(blob).group_max("g", "v") == {k: max(n) for k, n in baldes.items()}
        assert view(blob).group_count("g") == {k: len(n) for k, n in baldes.items()}
