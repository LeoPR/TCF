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

    def test_n_s_reservados_fail_loud(self):
        # 'n'/'s' estao no namespace (registry) mas NAO sao decodaveis ainda (encoder nunca emite) ->
        # fail-loud 'discriminador desconhecido', nao aceite-silencioso/crash cripto (verif. wf_85fcea32).
        with pytest.raises(ValueError, match="desconhecido"):
            decode("#TCF.8n\n1\n2\n3\n")
        with pytest.raises(ValueError, match="desconhecido"):
            decode("#TCF.8s\nfoo\nbar\n")

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
    """#4a/#4b: lista bool de topo vira '#TCF.8b...' (era .8H). FLOOR core vs denso. RT tipado."""

    def test_bool_vira_typed_e_rt(self):
        # #4b: pode ser modo CORE ('#TCF.8b\n') OU DENSO ('#TCF.8b1<n>\n') — ambos '#TCF.8b'.
        for vals in ([True, False, True, True], [True] * 8, [False] * 3,
                     [bool(i % 2) for i in range(6)], [True], [False], [False] * 40 + [True] * 24):
            w = encode(vals)
            assert w.startswith("#TCF.8b"), (vals, w[:16])
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


class TestBoolDensoFloor:
    """#4b: FLOOR core vs denso bN (w=1). O modo (a variavel `~`) e' argmin; RT tipado."""

    def test_floor_escolhe_por_regime(self):
        # constante/run -> core (seq-RLE esmaga); alternancia/ruido -> denso (bit-pack)
        assert encode([True] * 64)[7:8] == "\n"                  # all-true -> core
        assert encode([bool(i % 2) for i in range(64)])[7:8] == "1"  # alt -> denso (modo '1')

    def test_floor_nunca_pior(self):
        # o FLOOR nunca emite maior que qualquer um dos candidatos isolados
        for vals in ([True] * 50, [bool((i * 7) % 10 < 5) for i in range(50)],
                     [True, False] * 25, [False] * 50):
            w = encode(vals)
            assert decode(w) == vals

    def test_denso_rt_e_dominio_implicito(self):
        # forca denso (alternancia) e confere o dominio implicito false=0/true=1
        vals = [bool(i % 2) for i in range(64)]
        w = encode(vals)
        assert w.startswith("#TCF.8b1")                          # denso, modo '1'
        assert decode(w) == vals

    def test_denso_largura_invalida_fail_loud(self):
        with pytest.raises(ValueError, match="largura|invalid"):
            decode("#TCF.8b42\nAAAA")                            # w=4 p/ bool -> invalido

    def test_denso_adulterado_fail_loud(self):
        # INTEGRIDADE (verif. wf_85fcea32): wire denso adulterado para ALTO, nunca corrompe silencioso.
        w = encode([bool(i % 2) for i in range(24)])            # denso valido (n=24)
        head, _, b64 = w.partition("\n")
        with pytest.raises(ValueError, match="padding|payload|base64"):
            decode(head[:-2] + "3\n" + b64)                     # n rebaixado 24->3 (padding vira lixo)
        with pytest.raises(ValueError, match="base64|payload"):
            decode("#TCF.8b13\noA= =")                          # base64 nao-canonico (espaco no padding)
        with pytest.raises(ValueError, match="padding|payload|base64"):
            decode("#TCF.8b10\ngA==")                           # n=0 com payload -> nao ignora silencioso

    def test_denso_n0_vazio_ok(self):
        # n=0 com payload VAZIO e' o unico n=0 canonico -> [] (tolerante, inofensivo)
        assert decode("#TCF.8b10\n") == []
