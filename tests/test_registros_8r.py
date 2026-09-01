"""`#TCF.8R`: a forma da entrada e' metadado, nao rota (ADR-0049).

Uma `list[dict]` retangular e plana e' a mesma tabela que o `dict[str, list]` equivalente, e
passou a comprimir igual. O que a separa e' um caractere no header, o discriminador `R`, que
o `decode` le' pra remontar a lista de dicionarios.

O que esta suite protege, em ordem de importancia:

  1. o ROUND-TRIP, que e' o contrato;
  2. a FRONTEIRA, ou seja o que continua no `.8H` (e o que aconteceria se a fronteira vazasse:
     perda de capacidade calada, que e' a pior regressao possivel aqui);
  3. a DOMINANCIA, isto e' `.8R` nunca maior que o `.8H` que a mesma entrada emitia;
  4. a EQUIVALENCIA com o `.8M`, que e' o que torna o marcador barato.
"""
from __future__ import annotations

import pytest

from tcf import decode, encode
from tcf.hierarchical import _encode_hierarchical
from tcf.view import view
from tcf.wire import DISC_RECORDS, MAGIC_MULTI, MAGIC_RECORDS


def _b(w):
    return len(w.encode("utf-8"))


CASOS = {
    "uma-coluna-str": [{"a": "x"}, {"a": "y"}, {"a": "x"}],
    "duas-colunas": [{"uf": "SP", "v": "1"}, {"uf": "RJ", "v": "2"}],
    "baixa-cardinalidade": [{"uf": ["SP", "RJ", "MG", "BA"][i % 4]} for i in range(40)],
    "booleanos-como-str": [{"b": "1" if i % 2 else "0"} for i in range(50)],
    "int": [{"n": i} for i in range(30)],
    "float": [{"f": i / 4} for i in range(30)],
    "bool-nativo": [{"ok": i % 2 == 0} for i in range(30)],
    "com-nulo": [{"c": None if i % 3 == 0 else f"v{i}"} for i in range(30)],
    "tipos-mistos-por-coluna": [{"s": f"t{i}", "n": i, "b": i % 2 == 0} for i in range(20)],
    "uma-linha": [{"a": "x", "b": "y"}],
    "valor-vazio": [{"a": ""}, {"a": "x"}],
    "nome-com-acento": [{"endereço": "rua x"}, {"endereço": "rua y"}],
    "muitas-colunas": [{f"c{j}": f"{i}{j}" for j in range(12)} for i in range(5)],
}


@pytest.mark.parametrize("nome", list(CASOS))
def test_round_trip_exato(nome):
    """O contrato. Sem isto nada mais importa."""
    d = CASOS[nome]
    w = encode(d)
    assert w.startswith(MAGIC_RECORDS), f"{nome}: nao roteou pro .8R ({w[:12]!r})"
    assert decode(w) == d


@pytest.mark.parametrize("nome", list(CASOS))
def test_nunca_maior_que_o_8h_que_emitia_antes(nome):
    """DOMINANCIA: `corpo(.8M) = min(tcf, raw, dict, split) <= corpo(.8H) = tcf`.

    O `.8H` emite so' a rota `tcf`; o `.8M` a tem como UM dos candidatos do minimo. Logo o
    corpo nunca pode crescer, e os metas das duas familias declaram a mesma coisa. Se este
    teste falhar, a premissa do ADR-0049 caiu e a solda tem de voltar.
    """
    d = CASOS[nome]
    assert _b(encode(d)) <= _b(_encode_hierarchical(d))


@pytest.mark.parametrize("nome", list(CASOS))
def test_o_marcador_custa_zero_byte(nome):
    """O `R` OCUPA o slot do `M`, nao soma. O wire e' o do `.8M` com um caractere trocado."""
    d = CASOS[nome]
    colunas = {k: [r[k] for r in d] for k in d[0]}
    w_r, w_m = encode(d), encode(colunas)
    assert _b(w_r) == _b(w_m)
    assert w_r[len(MAGIC_MULTI):] == w_m[len(MAGIC_MULTI):]
    assert w_r[6] == DISC_RECORDS and w_m[6] == "M"


def test_a_mesma_tabela_nas_duas_grafias_da_o_mesmo_corpo():
    """A ideia inteira, num teste: a grafia da entrada nao muda mais o que se paga."""
    regs = [{"uf": "SP", "v": "1"}, {"uf": "RJ", "v": "2"}, {"uf": "SP", "v": "3"}]
    cols = {"uf": ["SP", "RJ", "SP"], "v": ["1", "2", "3"]}
    assert encode(regs)[7:] == encode(cols)[7:]
    assert decode(encode(regs)) == regs      # cada uma volta NA FORMA EM QUE ENTROU
    assert decode(encode(cols)) == cols


# ---------------------------------------------------------------- a fronteira

NAO_E_TABELA = {
    "ragged": [{"a": 1, "b": 2}, {"a": 3}],
    "aninhado": [{"a": {"x": 1}}],
    "array-na-celula": [{"a": [1, 2]}],
    "chaves-fora-de-ordem": [{"a": 1, "b": 2}, {"b": 3, "a": 4}],
    "chave-nao-str": [{1: "v"}],
    "sem-chave": [{}],
    "lista-de-escalares": ["a", "b"],
    "lista-mista": [{"a": 1}, "b"],
}


@pytest.mark.parametrize("nome", list(NAO_E_TABELA))
def test_o_que_nao_e_tabela_nao_muda_de_rota(nome):
    """A canonizacao RECUSA o que nao e' tabela, e o recusado sai byte-identico ao de antes."""
    d = NAO_E_TABELA[nome]
    try:
        w = encode(d)
    except Exception as e:                      # chave nao-str levanta, e continua levantando
        assert type(e).__name__ in ("HierarchicalError", "ValueError"), nome
        return
    assert not w.startswith(MAGIC_RECORDS), f"{nome}: nao deveria ter roteado pro .8R"


QUEBRA_DE_LINHA = {
    "lf-no-valor": [{"a": "x\ny"}, {"a": "z"}],
    "cr-no-valor": [{"a": "x\rz"}, {"a": "w"}],
    "crlf-no-valor": [{"a": "x\r\ny"}, {"a": "z"}],
    "lf-no-nome": [{"a\nb": "x"}],
    "cr-no-nome": [{"a\rb": "x"}],
}


@pytest.mark.parametrize("nome", list(QUEBRA_DE_LINHA))
def test_quebra_de_linha_fica_no_8h_e_o_rt_continua_exato(nome):
    """A guarda que impede a REGRESSAO CALADA mais séria desta solda.

    O `.8H` escapa folhas e nomes; o `.8M` os recusa, porque o wire é LF-only e o LF separa
    o meta. Rotear estes casos trocaria um round-trip que funciona por um `ValueError`: o
    usuario perderia uma capacidade que tinha, sem pedir e sem aviso. Eles ficam no `.8H`.
    """
    d = QUEBRA_DE_LINHA[nome]
    w = encode(d)
    assert w.startswith("#TCF.8H"), f"{nome}: deveria ficar no .8H, veio {w[:12]!r}"
    assert decode(w) == d


# ------------------------------------------------------------------- contratos

def test_sort_by_e_recusado_com_mensagem_que_ensina():
    """Deliberadamente NAO liberado junto com a solda (ADR-0049).

    Rotear registros faz o `sort_by` chegar ao ramo flat, onde ele funcionaria. So' que ele
    e' order-free: devolveria a lista do usuario REORDENADA. Trocar um erro alto por um
    reordenamento calado e' o silencio que este formato recusa.
    """
    with pytest.raises(ValueError, match="sort_by nao vale em lista de registros"):
        encode([{"a": "2"}, {"a": "1"}], sort_by="a")
    # e no dict de colunas ele continua valendo, que e' onde a troca de ordem e' declarada
    assert encode({"a": ["2", "1"]}, sort_by="a") is not None


def test_schema_sobrevive_ao_roteamento():
    """A decisao de aplicar o spec e' a mesma; o wire e' que fica menor."""
    ips = ["203.47.211.94", "178.54.193.67", "191.86.245.32"] * 4
    d = [{"c": v} for v in ips]
    w = encode(d, schema={"c": "ip"})
    assert w.startswith(MAGIC_RECORDS)
    assert decode(w) == d
    assert _b(w) < _b(_encode_hierarchical(d))


def test_a_view_le_o_8r_como_a_tabela_que_ele_e():
    """Pra view a forma de origem nao importa: o corpo guarda COLUNAS, e e' o que ela serve."""
    d = [{"uf": ["SP", "RJ", "MG"][i % 3], "v": str(i)} for i in range(30)]
    v = view(encode(d))
    assert v.columns == ["uf", "v"]
    assert v.nrows == 30
    assert sum(v.group_count("uf").values()) == 30
    assert v.group_sum("uf", "v") == view(encode(
        {"uf": [r["uf"] for r in d], "v": [r["v"] for r in d]})).group_sum("uf", "v")


def test_discriminador_desconhecido_continua_falhando_alto():
    """Reservar o `R` nao pode ter aberto a porta pra qualquer letra."""
    with pytest.raises(ValueError, match="discriminador"):
        decode("#TCF.8Z@a\nx\n")


def test_o_8r_de_zero_linhas():
    """Borda: lista vazia NAO e' registros (nao ha' chave), e segue no single-col vazio."""
    assert encode([]) == "#TCF.8\n"
    assert decode(encode([])) == []
