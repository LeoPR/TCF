"""Weld #4 — single-col TIPADO (#TCF.8<tag>). Decode = pre-avaliador de apelidos.

#4a (este arquivo, decode): o decode passa a aceitar `#TCF.8<tag>\n<corpo-core>` (modo CORE), expande
pro corpo core (reusa `_decode_column`) e casta pro tipo. A variavel `modo` (o conceito do `~`) e'
deduzida da POSICAO (indice 7) — NAO ha `~` no wire. Modo denso bN = reservado (#4b, fail-loud).

Nota de design (owner 2026-07-24): a funcao e' acionada pela VARIAVEL, nao pelo caractere; o `~` e'
categoria 4 (nunca byte de wire, so' nome interno). Ver notas 2026-07-24-0100/0322.
"""
import pytest

from tcf import encode, decode


def _typed_core_wire(vals, tag, render):
    """Constroi um wire tipado-core a mao: '#TCF.8<tag>\n' + corpo core dos literais renderizados."""
    body = encode([render(v) for v in vals]) if vals else ""
    return f"#TCF.8{tag}\n{body}"


class TestTypedSingleColDecode:
    def test_bool_core_roundtrip(self):
        for vals in ([True, False, True, True], [True] * 5, [False] * 3,
                     [bool(i % 2) for i in range(10)], [True], [False]):
            w = _typed_core_wire(vals, "b", lambda v: "true" if v else "false")
            back = decode(w)
            assert back == vals and all(isinstance(x, bool) for x in back), (vals, back)

    def test_number_core_roundtrip(self):
        assert decode(_typed_core_wire([1, 2, 3, 42], "n", str)) == [1, 2, 3, 42]
        assert decode(_typed_core_wire([1.5, 2.0, 3.25], "n", repr)) == [1.5, 2.0, 3.25]
        got = decode(_typed_core_wire([7, 3.5], "n", lambda v: repr(v) if isinstance(v, float) else str(v)))
        assert got == [7, 3.5] and isinstance(got[0], int) and isinstance(got[1], float)

    def test_string_core_identity(self):
        assert decode(_typed_core_wire(["a", "b", "ana"], "s", str)) == ["a", "b", "ana"]

    def test_bool_fora_do_dominio_fail_loud(self):
        # corpo com literal != true/false sob tag 'b' -> fail-loud (a tag CONSTRANGE o dominio)
        with pytest.raises(ValueError, match="dominio bool"):
            decode("#TCF.8b\nsim\n")

    def test_denso_reservado_fail_loud(self):
        # modo denso (char de largura no indice 7) ainda nao implementado -> fail-loud claro (#4b)
        with pytest.raises(ValueError, match="denso"):
            decode("#TCF.8b1\nZ")

    def test_tag_desconhecida_fail_loud(self):
        with pytest.raises(ValueError, match="desconhecido"):
            decode("#TCF.8z\nx")

    def test_aditivo_nao_muda_wires_existentes(self):
        # o ramo tipado NAO afeta as rotas existentes (orfao/multi/hier/vazio)
        assert decode(encode(["a", "b"])) == ["a", "b"]           # orfao
        assert decode(encode({"x": ["1", "2"]})) == {"x": ["1", "2"]}  # multi
        assert decode(encode([])) == []                            # vazio flat (weld #2)
        assert decode(encode([{"k": "v"}])) == [{"k": "v"}]        # .8H


class TestBoolEncodeTyped:
    """#4a-encode: lista bool de topo vira '#TCF.8b\n<core>' (era .8H). RT end-to-end tipado."""

    def test_bool_vira_typed_e_rt(self):
        for vals in ([True, False, True, True], [True] * 8, [False] * 3,
                     [bool(i % 2) for i in range(6)], [True], [False]):
            w = encode(vals)
            assert w.startswith("#TCF.8b\n"), (vals, w[:16])
            back = decode(w)
            assert back == vals and all(isinstance(x, bool) for x in back)

    def test_bool_menor_que_8h(self):
        # o envelope .8H (so' pra preservar o tipo) vira 1 char de tag -> menor
        vals = [True] * 32
        assert len(encode(vals).encode()) < len("#TCF.8H#V\\z#:32[]:...b".encode()) + 40

    def test_nao_flipa_int_float_str_mixed(self):
        assert encode([1, 2, 3]).startswith("#TCF.8H")            # int -> .8H (nao flipado)
        assert encode([1.5, 2.0]).startswith("#TCF.8H")           # float -> .8H
        assert not encode(["a", "b"]).startswith("#TCF.8")        # str -> orfao
        with pytest.raises(ValueError, match="MISTOS|union|misto"):
            encode([True, 1])                                     # mixed bool+int -> fail-loud
