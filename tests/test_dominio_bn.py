"""bN de dominio — weld 2026-07-27 (`composicional/dominio_bn.py`, ADR-0036).

Cada teste aqui corresponde a um achado medido nos labs
`experiments/lab/dirty/2026-07/2026-07-27/{1608,1647,2211,2231,2247}`.
"""
from __future__ import annotations

import pytest

from tcf import decode, encode
from tcf.composicional.dominio_bn import (
    DISC_LOTE, DISC_STREAM, MARCADOR, MAX_W, candidatos, dominio,
)
from tcf.encoder import _encode_column


def _cands(valores):
    return candidatos(valores, lambda vs: _encode_column(vs, header="val"), None)


class TestFloorNuncaPior:
    @pytest.mark.parametrize("dados", [
        ["v0"] * 200,                                   # k=1: o core resolve com RLE
        ["x"],
        [],
        [f"user{i}@dominio{i}.com" for i in range(200)],  # alta cardinalidade
        [f"{i:09d}" for i in range(200)],
    ])
    def test_nao_piora(self, dados):
        """O bN e' candidato do `min()`. Nenhuma coluna pode sair maior por causa dele."""
        assert decode(encode(dados)) == dados

    def test_k1_fica_com_o_core(self):
        """`k<=1`: RLE `*N|valor` e' otimo, e o bN nem se qualifica."""
        assert _cands(["v0"] * 200) == []
        assert encode(["v0"] * 200).startswith("#TCF.8\n")


class TestCardinalidadeBaixa:
    @pytest.mark.parametrize("k", [2, 3, 4, 5, 6, 7, 8, 16])
    def test_escada_ativa_e_roundtrip(self, k):
        rot = [f"valor-{j}" for j in range(k)]
        dados = [rot[i % k] for i in range(200)]
        w = encode(dados)
        assert w[6] == DISC_STREAM, f"k={k} devia usar bN: {w.splitlines()[0]!r}"
        assert decode(w) == dados

    def test_binario_string_encolhe(self):
        """O caso que abriu a investigacao: 200 valores `"0"`/`"1"`."""
        dados = [str(i % 2) for i in range(200)]
        antes = len(("#TCF.8\n" + _encode_column(dados)).encode())
        depois = len(encode(dados).encode())
        assert depois < antes // 5, f"{antes} -> {depois}"
        assert decode(encode(dados)) == dados


class TestSlotNulo:
    def test_null_e_mais_um_slot(self):
        dados = [None if i % 9 == 0 else ["a", "b", "c"][i % 3] for i in range(200)]
        assert dominio(dados)[0] is None, "null ocupa o slot 0 pre-alocado"
        obtido = decode(encode(dados))
        assert obtido == dados
        assert [i for i, x in enumerate(obtido) if x is None] == \
               [i for i, x in enumerate(dados) if x is None]

    def test_zero_como_dado_nao_vira_null(self):
        """A colisao que ja' custou 4 bugs: `0` cru = slot nulo, `\\0` = o literal."""
        dados = [None if i % 3 == 0 else "0" for i in range(60)]
        obtido = decode(encode(dados))
        assert obtido == dados
        assert obtido.count("0") == dados.count("0")
        assert obtido.count(None) == dados.count(None)


class TestMarcadorEEscape:
    def test_valor_que_comeca_com_o_marcador(self):
        dados = [MARCADOR + "SOMA(A1)", "normal", "outro"] * 40
        assert decode(encode(dados)) == dados

    def test_todos_comecam_com_o_marcador(self):
        """Pior caso: 1 escape por valor do dominio. Continua correto."""
        dados = [MARCADOR + c for c in "abc"] * 40
        assert decode(encode(dados)) == dados

    def test_valor_que_ja_traz_backslash(self):
        """O core escapa o proprio `\\`; desfazer demais mutilaria o dado."""
        dados = [chr(92) + "temp", "normal", "outro"] * 40
        assert decode(encode(dados)) == dados

    def test_valor_vazio_no_dominio(self):
        dados = ["", "a", "b"] * 40
        assert decode(encode(dados)) == dados


class TestModoLote:
    def test_C_nao_e_emitido_por_default(self):
        """`C` e' ~1 B menor mas NAO STREAMA — nao pode vencer um `min()` cego."""
        dados = [str(i % 2) for i in range(200)]
        assert encode(dados)[6] == DISC_STREAM

    def test_C_continua_decodavel(self):
        """Wire produzido por outra ponta tem de ser lido."""
        dados = [str(i % 2) for i in range(200)]
        lote = _cands(dados)[1]
        assert lote[6] == DISC_LOTE
        assert decode(lote) == dados

    def test_C_e_menor_que_B(self):
        dados = [str(i % 2) for i in range(200)]
        b, c = _cands(dados)
        assert len(c.encode()) < len(b.encode())


class TestFailLoud:
    @pytest.mark.parametrize("wire", [
        "#TCF.8B\n",                                    # sem largura
        "#TCF.8Bx5\n",                                  # largura nao-numerica
        "#TCF.8B9" + "5\n",                             # largura > MAX_W
        "#TCF.8B1zz\nabc\n=AA",                         # contagem nao-hex
        "#TCF.8B15\na\nb\n",                            # sem marcador
        "#TCF.8B15",                                    # sem corpo
    ])
    def test_cabecalho_ou_fronteira_invalidos(self, wire):
        with pytest.raises(ValueError):
            decode(wire)

    def test_indice_fora_do_dominio(self):
        """`w` bits enderecam 2^w slots; indice alem do dominio e' wire adulterado."""
        with pytest.raises(ValueError):
            decode("#TCF.8B22\na\nb\n=/w")

    def test_largura_maxima_declarada(self):
        assert MAX_W == 8, "o namespace vai de w=1 a w=8 (ate' 256 valores)"
