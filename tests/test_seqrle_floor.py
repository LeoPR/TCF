"""FLOOR do seq-RLE — o marcador `*N+delta|` só entra se ENCOLHER.

Achado do owner olhando um wire de inteiros aleatórios: o encoder emitia marcadores de delta
em dado sem cadência, e o marcador custava mais do que economizava —

    *2+498217|\\168116   17 B     vs     \\168116 + \\666333 + 2 LF   16 B

`hcc_seqrle.encode` aplicava `compact_body` INCONDICIONALMENTE; o custo do marcador nunca
entrava na decisão. Medido no lab 2026-07-25-2107: piorava em 7 de 16 casos, ~8-9% do corpo
em ruído de alta cardinalidade.

Agora é `min(compactado, bruto)` — mesmo padrão do `min()` do multi-col e do modo tipado.
"""
import dataclasses

import pytest

from tcf import decode, encode
from tcf.encoder import _encode_column
from tcf.pipeline import DEFAULT_PIPELINE

SEM_SEQRLE = dataclasses.replace(DEFAULT_PIPELINE, hcc_seq_rle=False)


def _lcg(seed):
    x = seed
    while True:
        x = (1103515245 * x + 12345) % (2 ** 31)
        yield x


def _ruido(n, k, seed=7):
    g = _lcg(seed)
    return [str(next(g) % k) for _ in range(n)]


class TestNuncaPior:
    """A propriedade que o FLOOR garante: o corpo emitido nunca é maior que o bruto."""

    @pytest.mark.parametrize("col", [
        _ruido(100, 10), _ruido(100, 100), _ruido(100, 10 ** 6),
        _ruido(1000, 10 ** 6),
        [str(i) for i in range(1000)],                       # cadência limpa
        [str(i * 5) for i in range(200)],
        [f"2026-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}" for i in range(200)],
        [f"user{i}@dominio{i % 7}.com" for i in range(200)],
        [f"{i * 2654435761 % (16 ** 8):08x}-a" for i in range(200)],
    ])
    def test_corpo_nunca_maior_que_o_bruto(self, col):
        com = _encode_column(col)
        bruto = _encode_column(col, cfg=SEM_SEQRLE)
        assert len(com.encode()) <= len(bruto.encode()), (
            f"seq-RLE piorou: {len(com.encode())} > {len(bruto.encode())}")


class TestOndeGanhaSegueGanhando:
    """O FLOOR é `min`, não um desligamento — a cadência tem que continuar colapsando."""

    def test_sequencial_colapsa(self):
        """1000 inteiros viram 3 marcadores (a corrida QUEBRA a cada largura de digito:
        1..9, 10..99, 100..999) — nao 1, mas ainda ~31 B."""
        corpo = _encode_column([str(i) for i in range(1000)])
        assert len(corpo.encode()) < 60, corpo[:80]
        assert corpo.count("*") == 3, corpo

    def test_ids_consecutivos_colapsam(self):
        """Largura constante (6 digitos) => UM marcador so'."""
        corpo = _encode_column([str(100000 + i) for i in range(200)])
        assert len(corpo.encode()) < 40, corpo[:80]
        assert corpo.count("*") == 1, corpo

    def test_passo_nao_unitario_colapsa(self):
        corpo = _encode_column([str(i * 5) for i in range(200)])
        assert len(corpo.encode()) < 60, corpo[:80]
        assert "+5|" in corpo, corpo


class TestFloorBarraOMarcadorCaro:
    """Em ruído de alta cardinalidade o marcador não paga — e agora não é emitido."""

    def test_ruido_nao_leva_marcador_de_delta(self):
        corpo = _encode_column(_ruido(100, 10 ** 6))
        assert "*2+" not in corpo and "*2-" not in corpo, corpo[:120]

    def test_economia_medida(self):
        """Regressão do ganho: o caso pior do lab (ruído 1e6, n=1000)."""
        col = _ruido(1000, 10 ** 6)
        assert len(_encode_column(col).encode()) <= len(_encode_column(col, cfg=SEM_SEQRLE).encode())


class TestRoundTripPreservado:
    @pytest.mark.parametrize("dados", [
        [int(s) for s in _ruido(100, 10 ** 6)],
        list(range(500)),
        [i * 5 for i in range(200)],
        [None if i % 7 == 0 else i for i in range(100)],
        [f"user{i}@d{i % 5}.com" for i in range(100)],
    ])
    def test_rt(self, dados):
        assert decode(encode(dados)) == dados
