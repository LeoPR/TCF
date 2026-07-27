"""Delimitador de POLARIDADE — weld 2026-07-26 (`composicional/polaridade.py`).

Cobre o que os labs `2026-07-26-{1853,1913,1954,2126}` mediram e o que a auditoria
adversarial do `2126` reproduziu. Cada bug que ela achou virou um teste aqui.
"""
from __future__ import annotations

import pytest

from tcf import decode, encode
from tcf.composicional.polaridade import FAIXA, despolariza, le_sufixo, polariza
from tcf.encoder import _encode_column


def _cpf_mascara(n):
    """MASCARA, nao documento: sem calculo de digito verificador. Nenhum CPF valido."""
    return [f"{i % 1000:03d}.{i * 7 % 1000:03d}.{i * 13 % 1000:03d}-{i % 100:02d}"
            for i in range(n)]


class TestFaixa:
    def test_faixa_nao_tem_digito(self):
        """Digito eleito FUNDE com a corrida que deveria delimitar (auditoria 2026-07-26).

        Com `0` eleito, `1\\22.\\33` vira `1022.33` e a volta deixa de ser exata.
        """
        assert not any(c.isdigit() for c in FAIXA)

    def test_faixa_nao_tem_letra(self):
        """Letra eleita colide com o slot do DISCRIMINADOR (auditoria 2026-07-26).

        O sufixo pousa no indice 6 — onde vivem `b`, `n`, `s`, `H`, `M`. Uma coluna de
        STRING elegia `b` e emitia `#TCF.8b`, byte-identico ao cabecalho de uma coluna bool.
        """
        assert not any(c.isalpha() for c in FAIXA)

    def test_faixa_nao_tem_gramatica(self):
        assert not (set(FAIXA) & set("*~^,|" + chr(92) + "\n"))

    def test_sufixo_nunca_colide_com_discriminador(self):
        """Nenhum discriminador de hoje e' pontuacao — a separacao tag/sufixo e' inequivoca."""
        assert not (set(FAIXA) & {"M", "H", "b", "n", "s", " ", ""})


class TestFloorNuncaPior:
    @pytest.mark.parametrize("dados", [
        ["palavra" + chr(97 + i % 26) for i in range(50)],          # texto: sem digito
        ["S" if i % 2 else "N" for i in range(50)],                 # binario nao-numerico
        [str(i % 2) for i in range(50)],                            # "0"/"1": 2 escapes so'
        ["x"],
        [""],
    ])
    def test_recusa_quando_nao_paga(self, dados):
        """FLOOR inclui o custo do PROPRIO sufixo. Empate fica com a grafia de hoje."""
        sufixo, corpo = polariza(_encode_column(dados))
        assert sufixo == ""
        assert corpo == _encode_column(dados)

    def test_nunca_aumenta_o_wire(self):
        """Nenhuma coluna pode sair MAIOR do que a grafia de hoje."""
        casos = [_cpf_mascara(50), ["palavra" + chr(97 + i % 26) for i in range(50)],
                 [f"{i:03d}.{i * 3 % 1000:03d}" for i in range(50)],
                 [f"user{i}@d{i % 9}.com" for i in range(50)]]
        for dados in casos:
            corpo = _encode_column(dados)
            sufixo, novo = polariza(corpo)
            assert len(novo.encode()) + len(sufixo.encode()) <= len(corpo.encode())


class TestRoundTrip:
    @pytest.mark.parametrize("dados", [
        _cpf_mascara(50),
        ["-".join(f"{(i * 37) % 10000:04d}" for _ in range(4)) for i in range(30)],
        [f"{i:03d}.{i * 3 % 1000:03d}" for i in range(50)],
        [None if i % 6 == 0 else str(i * 37 % 100000) for i in range(50)],
        [None if i % 6 == 0 else ("0" if i % 5 == 0 else f"{i:03d}.{i * 3 % 1000:03d}")
         for i in range(50)],
    ])
    def test_despolariza_reconstroi_o_canonico_byte_a_byte(self, dados):
        corpo = _encode_column(dados)
        sufixo, novo = polariza(corpo)
        if sufixo:
            assert despolariza(novo, sufixo) == corpo

    @pytest.mark.parametrize("dados", [
        _cpf_mascara(200),
        [True, False, True] * 10,
        [True, None, False] * 10,
        [None if i % 6 == 0 else i * 37 % 100000 for i in range(50)],
        [None if i % 7 == 0 else round(i * 13 % 10000 / 100, 2) for i in range(50)],
        ["0"] * 10,
        [None if i % 3 == 0 else "0" for i in range(30)],
        [],
        ["x"],
    ])
    def test_rt_publico_valor_e_tipo(self, dados):
        """RT ESTRITO: valor E tipo, elemento a elemento, com guarda de comprimento.

        Um `"0"` virando `None` mantem o tamanho da lista e o tipo `list` — passaria num RT
        frouxo. Foi assim que o lab `2126` pegou o bug do slot nulo.
        """
        obtido = decode(encode(dados))
        assert len(obtido) == len(dados)
        assert obtido == dados
        assert all(type(a) is type(b) for a, b in zip(obtido, dados))


class TestSlotNulo:
    def test_null_e_referencia_nao_literal(self):
        """O `0` do slot nulo NAO e' caso especial: e' referencia, e a polaridade acerta.

        A primeira versao tratava a linha `0` como opaca "porque e' o null" — polaridade-cega.
        Sob polaridade `L` o `0` cru ja' e' o LITERAL `"0"`; e' o null que precisa da troca.
        """
        dados = [None if i % 6 == 0 else ("0" if i % 5 == 0 else
                 f"{i:03d}.{i * 3 % 1000:03d}") for i in range(50)]
        w = encode(dados)
        assert w.split("\n")[0] != "#TCF.8", "esta coluna deve ATIVAR a polaridade"
        obtido = decode(w)
        assert obtido == dados
        assert [i for i, x in enumerate(obtido) if x is None] == \
               [i for i, x in enumerate(dados) if x is None]


class TestCabecalho:
    def test_sufixo_depois_da_tag(self):
        dados = [None if i % 6 == 0 else i * 37 % 100000 for i in range(50)]
        linha0 = encode(dados).split("\n")[0]
        assert linha0.startswith("#TCF.8n")

    def test_le_sufixo_fail_loud(self):
        for ruim in ("", "!!!", "!?", "b", "0"):
            with pytest.raises(ValueError):
                le_sufixo(ruim)

    def test_le_sufixo_ok(self):
        assert le_sufixo("!") == ("!", "R")
        assert le_sufixo("!!") == ("!", "L")

    def test_wire_adulterado_falha_alto(self):
        """Sufixo declarado mas corpo sem o delimitador nao pode corromper em silencio."""
        with pytest.raises(ValueError):
            decode("#TCF.8@@@\nabc\n")

    def test_orfao_nao_polariza(self):
        """`stamp=False` nao tem cabecalho onde declarar — segue canonico."""
        dados = _cpf_mascara(50)
        assert encode(dados, stamp=False) == _encode_column(dados)


class TestRotasNaoSoldadas:
    """O weld e' single-col (stamp + tipado). Multi/hierarquico ficaram de fora."""

    def test_multi_col_intocado(self):
        cols = {"a": [f"{i:03d}.{i * 3 % 1000:03d}" for i in range(20)],
                "b": [f"{i:04d}" for i in range(20)]}
        w = encode(cols)
        assert w.startswith("#TCF.8M")
        assert decode(w) == cols

    def test_hierarquico_intocado(self):
        dados = {"a": [{"x": "1"}, {"x": "2"}]}
        w = encode(dados)
        assert decode(w) == dados
