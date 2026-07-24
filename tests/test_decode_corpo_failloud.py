"""Weld 2026-07-24 — FAIL-LOUD no corpo core malformado (`syntax.decode`/`_parse_decl`).

Origem: lab 2026-07-24-1832 (fechamento hex-n). A bateria de corrupcao achou 42 `KeyError`
crus; reproduzi no ORFAO PURO (sem tag `b`, sem weld do ramo tipado) => lacuna PRE-EXISTENTE
do core generico, nao regressao do #4a/#4b.

Varredura posterior achou mais 4 sitios da MESMA CLASSE — e um deles era PIOR que crash:
`^0` caia em `nos_decl[-1]` (indice negativo do Python) e devolvia o ULTIMO no' declarado,
CALADO. Corrupcao silenciosa > crash na escala de gravidade do projeto.

Contrato: wire produzido pelo encoder NUNCA cai nestes ramos (garantia do owner). Sao todos
caminho-de-erro => BYTE-NEUTRO por construcao (baselines D1-D9/D17a/real-world intactos).
"""
import pytest

from tcf import encode, decode


class TestCorpoMalformadoFailLoud:
    """Todo corpo nao-canonico levanta ValueError com mensagem acionavel — nunca crash cru."""

    @pytest.mark.parametrize("wire,trecho", [
        ("9rue\n",           "fragmento inexistente"),   # o achado original do lab 1832
        ("ab\n1~9\n",        "fragmento inexistente"),   # pendente dentro de composicao
        ("ab\ncd\n0..9\n",   "fragmento inexistente"),   # range estourando a faixa
        ("ab\n^7\n",         "fora de faixa"),           # ref de linha alta
        ("ab\n^x\n",         "referencia de linha invalida"),
        ("ab\n*|cd\n",       "contador RLE invalido"),
        ("ab\n*x|cd\n",      "contador RLE invalido"),
    ])
    def test_fail_loud_com_mensagem(self, wire, trecho):
        with pytest.raises(ValueError, match=trecho):
            decode(wire)

    def test_ref_zero_nao_e_aceite_silencioso(self):
        """REGRESSAO da corrupcao silenciosa: '^0' devolvia nos_decl[-1] (o ultimo no')."""
        with pytest.raises(ValueError, match="fora de faixa"):
            decode("ab\ncd\n^0\n")

    def test_propaga_pelo_ramo_tipado(self):
        """A tag `b` nao mascara nem re-embrulha: o fail-loud do core atravessa."""
        with pytest.raises(ValueError, match="fragmento inexistente"):
            decode("#TCF.8b\n9rue\n")


class TestLoopInfinito:
    """Achado do lab 2026-07-24-2010 — a classe MAIS grave: nao era excecao, era HANG.

    Um '~' em inicio de segmento nao era consumido por ramo nenhum do `_parse_decl`: o laco
    interno dava `break` sem avancar `i` e o `while` externo nunca progredia. Alem de travar,
    `frags` crescia a cada volta (memoria sem teto) — wire de 8 B derrubava o processo.

    Guard de PROGRESSO (generico): iteracao que nao consome 1 char => fail-loud.
    """

    @pytest.mark.parametrize("wire", [
        "ab\n*~2\n",        # o caso exato que travou o lab
        "ab\n~x\n",         # '~' na posicao 0 do segmento
        "ab\n*~\n",
        "#TCF.8b\n*~2\n",   # atraves do ramo tipado
    ])
    def test_nao_trava_e_fail_loud(self, wire):
        with pytest.raises(ValueError, match="caractere inesperado"):
            decode(wire)

    def test_til_legitimo_ainda_funciona(self):
        """O guard nao pode matar o '~' VALIDO (separador de composicao, sempre apos digito)."""
        dados = [f"pedido-2026-{i:04d}" for i in range(30)]
        wire = encode(dados)
        assert "~" in wire                    # confirma que este wire exercita composicao
        assert decode(wire) == dados


class TestByteNeutro:
    """O weld e' caminho-de-erro: wire VALIDO decoda identico e o encode nao muda 1 byte."""

    @pytest.mark.parametrize("dados", [
        ["ab", "cd", "ab"],                       # exercita ref de linha '^N'
        ["x"] * 40,                               # exercita RLE '*N|'
        ["pre" + s for s in ("aa", "bb", "cc")],  # exercita fragmento/composicao
        [f"item-{i:03d}" for i in range(60)],
        [""], ["", ""], ["a"],
    ])
    def test_roundtrip_intacto(self, dados):
        assert decode(encode(dados)) == dados

    def test_ref_de_linha_valida_ainda_funciona(self):
        """Faixa 1..len e' INCLUSIVA nas duas pontas — o guard nao pode cortar '^1' nem '^len'."""
        assert decode("ab\n^1\n") == ["ab", "ab"]
        assert decode("ab\ncd\n^2\n") == ["ab", "cd", "cd"]
        assert decode("ab\ncd\n^1\n") == ["ab", "cd", "ab"]
