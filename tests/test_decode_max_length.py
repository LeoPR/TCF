"""Teto de descompressao (`max_length`) — weld 2026-07-24.

Achado medido no lab 2026-07-24-2010 (parte D): `*N|` nao tinha teto — 15 B de wire
materializavam 1e9 elementos (~8 GB). Classe zip-bomb / billion-laughs.

Desenho (owner): "seguir a tradicao, nao reinventar". Nome `max_length` e a convencao
`0 == sem teto` vem do zlib/bz2/lzma. UNIDADE = elementos decodificados (o que a bomba
aloca e' a lista), nao bytes. Wire produzido pelo `encode` nunca encosta no teto.
"""
import pytest

from tcf import decode, encode
from tcf.composicional.syntax import MAX_LENGTH_PADRAO


class TestBombaBarrada:
    """Os tres vetores medidos no lab, cada um por um caminho de expansao distinto."""

    @pytest.mark.parametrize("wire,vetor", [
        ("x\n*999999999|y\n",        "core '*N|'"),
        ("x\n*99999999+1|y\n",       "seq-RLE '*N+d|' (expande ANTES do core)"),
        ("x\n" + "*9999|x\n" * 3000, "ACUMULADO — cada contador e' inocente (9999)"),
    ])
    def test_barra_por_default(self, wire, vetor):
        assert len(wire) < 30_000, vetor          # wire minusculo => amplificacao
        with pytest.raises(ValueError, match="excede o teto"):
            decode(wire)

    def test_mensagem_ensina_o_override(self):
        """Fail-loud aqui NAO pode ser warning: quando se avisa, a memoria ja' foi. Entao a
        mensagem tem que dizer qual parametro subir."""
        with pytest.raises(ValueError, match="max_length"):
            decode("x\n*999999999|y\n")


class TestOverride:
    def test_teto_maior_libera(self):
        assert len(decode("x\n*2000|y\n", max_length=5_000)) == 2001

    def test_zero_e_sem_teto_convencao_zlib(self):
        assert len(decode("x\n*2000|y\n", max_length=0)) == 2001

    def test_teto_menor_aperta(self):
        with pytest.raises(ValueError, match="excede o teto"):
            decode("x\n*2000|y\n", max_length=100)

    @pytest.mark.parametrize("bad", [-1, "x", 1.5])
    def test_valor_invalido_fail_loud(self, bad):
        with pytest.raises(ValueError, match="max_length deve ser int"):
            decode("a\n", max_length=bad)


class TestNaoAfetaWireLegitimo:
    """Garantia do owner: o que o TCF gera nunca encosta no teto."""

    def test_default_e_folgado(self):
        assert MAX_LENGTH_PADRAO >= 1_000_000

    @pytest.mark.parametrize("dados", [
        ["ok"] * 5000,                                   # RLE denso legitimo
        [f"pedido-2026-{i:05d}" for i in range(5000)],   # composicao/seq-RLE
        [i % 3 == 0 for i in range(5000)],               # ramo tipado
    ])
    def test_roundtrip_intacto(self, dados):
        assert decode(encode(dados)) == dados

    def test_multi_col_tambem_protegido(self):
        """`_decode_column` e' funil unico: multi/view/hierarquico herdam o teto mesmo
        sem expor o override."""
        tabela = {"a": ["x"] * 500, "b": [str(i) for i in range(500)]}
        assert decode(encode(tabela)) == tabela
