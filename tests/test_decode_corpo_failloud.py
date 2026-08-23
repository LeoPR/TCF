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

    def test_ref_zero_e_o_slot_reservado(self):
        """REGRESSAO da corrupcao silenciosa: `^0` devolvia `nos_decl[-1]` (o ULTIMO no'
        declarado), calado. Desde a pre-alocacao (slot 0 = null) `^0` tem significado
        proprio — o que NAO pode voltar e' ele resolver pra um no' de DADO."""
        assert decode("ab\ncd\n^0\n") == ["ab", "cd", None]      # nao 'cd'
        assert decode("ab\ncd\n0\n") == ["ab", "cd", None]       # grafia otimizada

    def test_ref_negativa_ainda_fail_loud(self):
        """A faixa agora comeca em 0, mas negativo segue fora dela (indice negativo do
        Python continuaria sendo corrupcao silenciosa)."""
        with pytest.raises(ValueError, match="fora de faixa"):
            decode("ab\ncd\n^-1\n")

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


class TestContadorRLEForaDoCanonico:
    """Weld 2026-08-23 (lab 2026-08-23-1420-reprova-rle-contador-zero): o parse do
    `*N|` aceitava contador 0, negativo e grafias com sinal — linha sumindo ou
    fantasma SEM erro (13/21 wires adulterados decodavam com dado errado). O
    encoder so' emite N >= 2 em digitos ASCII (runs iniciam em 2), entao todo o
    espaco rejeitado aqui e' INEMITIVEL — byte-neutro por construcao."""

    @pytest.mark.parametrize("wire,trecho", [
        ("ab\n*0|cd\n",    "fora do canonico"),      # linha declarada 0x: sumia calada
        ("ab\n*1|cd\n",    "fora do canonico"),      # N=1 inemitivel (encoder usa linha nua)
        ("ab\n*-3|cd\n",   "fora do canonico"),      # negativo: 0 copias E burlava o teto
        ("ab\n*+4|cd\n",   "fora do canonico"),      # sinal: int() cru aceitava
        ("ab\n*\u0664|cd\n", "contador RLE"),        # digito unicode (int() aceita; grafia nao)
        ("ab\n*0+1|5\n",   "contador RLE invalido"), # seq-RLE: emitia 1 linha fantasma (template)
        ("ab\n*1+1|5\n",   "contador RLE invalido"), # seq-RLE N=1 idem
    ])
    def test_contador_rejeitado(self, wire, trecho):
        with pytest.raises(ValueError, match=trecho):
            decode(wire)

    def test_rle_legitimo_intacto(self):
        """O canonico (N >= 2) segue decodando — e RT de dado com runs reais."""
        assert decode("ab\n*2|cd\n") == ["ab", "cd", "cd"]
        vals = ["x"] * 5 + ["y"] * 3
        assert decode(encode(vals)) == vals


class TestWireConcatenadoFailLoud:
    """Weld 2026-08-23 (lab 2026-08-23-1400-reprova-concat-corrompe): concatenar
    dois wires validos corrompia CALADO — as refs do segundo resolviam na tabela
    acumulada do primeiro (129/288 valores errados, 0 excecoes). A gramatica do
    corpo agora rejeita linha-header. Falso-positivo zero em corpo tcf:
    `_escape_lit` escapa runs de digito em literal, entao VALOR '#TCF.8...'
    nunca aparece bare (corpo raw e' verbatim e nao passa por este parser —
    limite documentado)."""

    def test_concat_dois_wires_stamp(self):
        w1 = encode(["ana", "bob", "ana", "bob", "carla"])
        w2 = encode(["rio", "sp", "rio", "bh", "sp"])
        with pytest.raises(ValueError, match="concatenad"):
            decode(w1 + w2)

    def test_concat_com_lf_extra(self):
        w1 = encode(["ana", "bob", "ana"])
        w2 = encode(["rio", "sp", "rio"])
        with pytest.raises(ValueError, match="concatenad"):
            decode(w1 + "\n" + w2)

    def test_header_bare_no_corpo(self):
        """A regra e' da GRAMATICA do corpo, nao da rota: qualquer '#TCF.<digito>'
        em linha de corpo tcf e' juncao, nunca dado (dado legitimo sai escapado)."""
        with pytest.raises(ValueError, match="concatenad"):
            decode("ab\ncd\n#TCF.8M@17\nef\n")

    def test_valor_que_imita_header_roundtrip(self):
        """CONTRA-PROVA do falso-positivo: valor literal '#TCF.8...' viaja escapado
        e o RT segue inteiro apos o guard."""
        vals = ["#TCF.8Mpedido", "comum", "#TCF.8Mpedido", "#TCF.9zz"]
        assert decode(encode(vals)) == vals
