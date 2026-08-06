"""Pre-alocacao de indices de referencia — slot 0 = null (owner 2026-07-24).

A tabela de referencias tem DUAS metades: slots altos vem do DADO (literais descobertos),
slots baixos vem do FORMATO (dicionario da versao, que NAO viaja no arquivo). A segunda
metade ja' existia — e' o dominio {false,true} do modo denso do bool (weld #4b). null e'
outra entrada dela, nao um caso com regra propria.

POR QUE INCONDICIONAL: `^N` sempre foi 1-based, entao `^0` era ESPACO MORTO. Ocupa-lo nao
tira endereco de ninguem — e evita que null consuma um endereco VIVO se fosse descoberto
como valor comum. Nada viaja no wire: a consistencia encode/decode vem da versao do formato.

ESCOPO DESTE WELD: so' o DECODE (resolucao de referencia). O encode ainda nao emite `^0`/`0`
— a rota flat exige `list[str]` (`_lista_flat`) e desvia coluna com `None` pro `.8H`. Abrir
essa rota e' o proximo weld, e e' onde mora o ganho de bytes (lab 2026-07-24-2210).
"""
import pytest

from tcf import decode, encode
from tcf.composicional.syntax import GRAFIA_NULO, NULO, _SLOTS_RESERVADOS


class TestSlot0:
    def test_referencia_explicita(self):
        assert decode("ab\ncd\n^0\n") == ["ab", "cd", None]

    def test_grafia_otimizada(self):
        """`0` e' a grafia otimizada de `^0` — a camada implicita expande p/ a explicita."""
        assert decode("ab\ncd\n0\n") == ["ab", "cd", None]

    def test_as_duas_grafias_sao_o_MESMO_valor(self):
        assert decode("ab\n^0\n") == decode("ab\n0\n")

    def test_null_nao_precisa_ser_declarado(self):
        """Slot pre-alocado: `^0` vale ANTES de qualquer declaracao (nao ha' 1o null que
        'declara' e demais que referenciam — todo null e' o mesmo endereco)."""
        assert decode("^0\n") == [None]
        assert decode("^0\nab\n^0\n") == [None, "ab", None]
        assert decode("0\nab\n0\n") == [None, "ab", None]

    def test_repeticao_adjacente(self):
        assert decode("*3|0\n") == [None, None, None]
        assert decode("ab\n*2|^0\ncd\n") == ["ab", None, None, "cd"]

    def test_constantes_do_formato(self):
        """Contrato: o slot 0 e' `None` e a grafia otimizada e' `0`. Se isso mudar, o wire
        muda — e' constante da VERSAO, nao detalhe interno."""
        assert _SLOTS_RESERVADOS == [NULO] and NULO is None
        assert GRAFIA_NULO == "0"


class TestNaoRoubaEnderecoDeDado:
    """O slot 0 era espaco morto: `^1` continua sendo o 1o no' declarado, byte-identico."""

    def test_ref_de_linha_inalterada(self):
        assert decode("ab\ncd\n^1\n") == ["ab", "cd", "ab"]
        assert decode("ab\ncd\n^2\n") == ["ab", "cd", "cd"]

    def test_faixa_valida_completa(self):
        base = "".join(f"{chr(ord('a') + i) * 2}\n" for i in range(5))
        for n in range(1, 6):
            assert decode(base + f"^{n}\n")[-1] == chr(ord("a") + n - 1) * 2

    @pytest.mark.parametrize("dados", [
        ["ab", "cd", "ab"], ["x"] * 40, [f"pedido-2026-{i:04d}" for i in range(30)],
        ["", "a", ""], ["0"], ["0", "1"], ["a", "0"],
    ])
    def test_roundtrip_intacto(self, dados):
        assert decode(encode(dados)) == dados

    def test_string_zero_nao_colide(self):
        """A string `"0"` e' escapada como `\\0` pelo core — nunca emite a linha `0` crua.
        Por isso o slot esta' livre (1179 colunas adversariais no lab 2026-07-24-2210)."""
        for col in (["0"], ["0", "0"], ["a", "0", "b"], ["0", "1", "10", "00"]):
            w = encode(col, stamp=False)
            assert "\n0\n" not in "\n" + w         # nenhuma linha inteira igual a '0'
            assert decode(w) == col


class TestEncodeEmiteNull:
    """Rota flat aberta p/ `str | None` (2026-07-25) — antes, 1 null expulsava a coluna
    inteira pro envelope `.8H`."""

    @pytest.mark.parametrize("col,wire", [
        ([None],                       "#TCF.8\n0\n"),
        ([None, None],                 "#TCF.8\n*2|0\n"),          # RLE sobre o slot
        (["a", None, "b"],             "#TCF.8\na\n0\nb\n"),
        ([None, "a", None],            "#TCF.8\n0\na\n0\n"),       # endereco ESTAVEL
        (["ok"] * 3 + [None] * 2,      "#TCF.8\n*3|ok\n*2|0\n"),
    ])
    def test_wire_exato(self, col, wire):
        assert encode(col) == wire
        assert decode(wire) == col

    def test_exemplo_do_owner(self):
        col = [None, "", "true", "false", "oi", None, "null"]
        w = encode(col)
        assert w == "#TCF.8\n0\n\ntrue\nfalse\noi\n0\nnull\n"
        assert decode(w) == col          # as 4 vias sobrevivem: null/""/"null"/literais

    def test_todo_null_e_o_mesmo_endereco(self):
        """Nao ha' '1o null declara, demais referenciam' — o slot e' pre-alocado."""
        w = encode([None, "x", None, "y", None])
        assert w.count("\n0\n") + w.endswith("\n0\n") >= 2
        assert "^" not in w              # nenhum null virou referencia a no' DECLARADO

    def test_null_nao_vira_string_vazia(self):
        """`_to_str` achatava None -> '' (perda SILENCIOSA de `null` != `""`)."""
        assert decode(encode([None, ""])) == [None, ""]
        assert encode([None]) != encode([""])

    def test_null_convive_com_qualquer_tag(self):
        """2026-07-25: a rota tipada foi generalizada e null passou a conviver com as tags.
        null nao pertence a um TIPO — e' a ausencia do valor, no slot 0."""
        assert encode([1, None, 3]).startswith("#TCF.8n\n")    # numero + null -> tipado
        # bool + null -> tipado. Weld b2 (2026-07-31, ADR-0037): o FLOOR escolhe o modo —
        # CORE ('#TCF.8b\n') ou DENSO TERNARIO ('#TCF.8b2<n>'). Com a grafia slot default
        # (2026-08-01, ADR-0038) o core de n=2 EMPATA com o b2 (12 = 12) e o FLOOR fica no
        # 1o candidato (core, mais inspecionavel). Nomes seguem decodaveis.
        assert encode([True, None]) == "#TCF.8b\n\\2\n0\n"     # bool + null -> core em slots
        assert decode(encode([1, None, 3])) == [1, None, 3]
        assert decode(encode([True, None])) == [True, None]

    def test_multi_col_com_null_ainda_no_8h(self):
        """LACUNA conhecida: a rota aberta e' a do single-col; multi-col c/ null segue no .8H."""
        assert encode({"a": ["x", None]}).startswith("#TCF.8H")
        assert decode(encode({"a": ["x", None]})) == {"a": ["x", None]}


class TestByteNeutroSemNull:
    """Coluna SEM null tem que sair byte-identica: o slot 0 nao rouba endereco."""

    @pytest.mark.parametrize("dados", [
        ["ativo", "inativo", "ativo"], ["x"] * 40,
        [f"pedido-2026-{i:04d}" for i in range(30)], ["", "a", ""], ["0", "1", "10"],
    ])
    def test_wire_nao_muda(self, dados):
        w = encode(dados)
        assert "0\n" != w[7:9] or dados[0] == "0"   # nao apareceu slot onde nao ha' null
        assert decode(w) == dados

    def test_gates_byte_canonicos_cobrem(self):
        """Guard-rail: os baselines D1-D9/real-world sao o gate real desta afirmacao."""
        import csv
        from pathlib import Path
        ds = Path(__file__).resolve().parent.parent / "datasets" / "synthetic"
        with (ds / "D1-emails-simples.csv").open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            vals = [row[0] for row in r if row]
        assert len(encode(vals).encode()) == 125       # pino do ADR-0034


class TestFailLoudPreservado:
    def test_fora_de_faixa(self):
        with pytest.raises(ValueError, match="fora de faixa"):
            decode("ab\n^9\n")

    def test_negativo(self):
        with pytest.raises(ValueError, match="fora de faixa"):
            decode("ab\n^-1\n")

    def test_nao_numerico(self):
        with pytest.raises(ValueError, match="referencia de linha invalida"):
            decode("ab\n^x\n")

    def test_zero_em_composicao_nao_vira_null(self):
        """Desambiguacao POSICIONAL: so' a linha INTEIRA igual a `0` e' o especial. Dentro de
        composicao o `0` segue sendo FRAGMENTO (inexistente -> fail-loud), entao 'compor uma
        string com null' permanece INEXPRIMIVEL na gramatica."""
        for corpo in ("ab\n1~0\n", "ab\ncd\n0..3\n", "ab\n0,1\n"):
            with pytest.raises(ValueError, match="fragmento inexistente"):
                decode(corpo)
