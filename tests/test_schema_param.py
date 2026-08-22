"""`schema=` — o parametro UNICO de spec da API publica (decisao owner).

Pina o CONTRATO da porta: formas aceitas, resolucao por name do registry, chave int =
POSICAO / str = NOME (ADR-0046: `''` e `'0'` sao nomes legitimos), fail-loud em tudo
que nao for uma das formas, e byte-neutralidade — o `schema=` so' escolhe qual spec
vai em qual coluna.
"""

import pytest

from tcf import (
    SPEC_CPF,
    SPEC_DATA_ISO,
    SPEC_INT_PAD,
    SPEC_IP,
    SPEC_REGISTRY,
    decode,
    encode,
)

# CPFs DV-validos ja' presentes na suite (nunca criar novos: regra do owner).
CPFS = ["529.982.247-25", "111.444.777-35", "398.727.888-40", "168.995.350-09"] * 10
IPS = [f"{10 + i % 5}.{i % 251}.{(i * 7) % 251}.{(i * 13) % 251}" for i in range(40)]


class TestExports:
    def test_os_5_specs_e_o_registry_sao_publicos(self):
        assert sorted(SPEC_REGISTRY) == ["cnpj", "cpf", "data-iso", "int-pad", "ip"]
        assert SPEC_REGISTRY["data-iso"] is SPEC_DATA_ISO
        assert SPEC_REGISTRY["int-pad"] is SPEC_INT_PAD


class TestFormasEquivalencia:
    """Formas equivalentes produzem wire BYTE-IDENTICO entre si."""

    def test_str_resolve_pelo_name_do_registry(self):
        assert encode(IPS, schema="ip") == encode(IPS, schema=SPEC_IP)

    def test_objeto_spec_direto(self):
        w = encode(IPS, schema=SPEC_IP)
        assert w.split("\n", 1)[0] == "#TCF.8 :ip"    # self-describing
        assert decode(w) == IPS

    def test_dict_por_nome(self):
        tab = {"ip": IPS, "obs": ["x"] * len(IPS)}
        assert encode(tab, schema={"ip": "ip"}) == encode(
            tab, schema={"ip": SPEC_IP}
        )

    def test_dict_por_posicao(self):
        tab = {"ip": IPS, "obs": ["x"] * len(IPS)}
        assert encode(tab, schema={0: "ip"}) == encode(
            tab, schema={"ip": SPEC_IP}
        )

    def test_dict_misto_posicao_e_nome(self):
        tab = {"ip": IPS, "cpf": CPFS[: len(IPS)], "obs": ["x"] * len(IPS)}
        assert encode(tab, schema={0: "ip", "cpf": "cpf"}) == encode(
            tab, schema={"ip": SPEC_IP, "cpf": SPEC_CPF}
        )

    def test_valor_none_e_coluna_sem_spec(self):
        tab = {"ip": IPS, "obs": ["x"] * len(IPS)}
        assert encode(tab, schema={"ip": "ip", "obs": None}) == encode(
            tab, schema={"ip": "ip"}
        )

    def test_dataset_8H_por_path(self):
        ds = [{"doc": c, "n": str(i)} for i, c in enumerate(CPFS)]
        w = encode(ds, schema={"doc": "cpf"})
        assert w == encode(ds, schema={"doc": SPEC_CPF})
        # ANTI-TAUTOLOGIA: os dois lados poderiam estar DROPANDO o spec, e a
        # igualdade passaria assim mesmo. O `:cpf` no meta prova que ele APLICOU.
        assert ":cpf" in w.split("\n", 1)[0]
        assert decode(w) == ds

    def test_roundtrip_com_schema(self):
        tab = {"ip": IPS, "cpf": CPFS[: len(IPS)]}
        assert decode(encode(tab, schema={0: "ip", 1: "cpf"})) == tab


class TestNomesQueParecemPosicao:
    """str = NOME sempre; int = POSICAO sempre. Sem adivinhacao."""

    def test_coluna_chamada_0_e_um_nome(self):
        tab = {"x": ["a"] * len(IPS), "0": IPS}
        w = encode(tab, schema={"0": "ip"})           # NOME "0" = 2a coluna
        assert w == encode(tab, schema={"0": SPEC_IP})
        w2 = encode(tab, schema={0: "ip"})            # POSICAO 0 = coluna "x"
        assert w2 != w                                # aplicou noutra coluna
        assert decode(w) == tab

    def test_coluna_de_nome_vazio_adr_0046(self):
        tab = {"": CPFS[: len(IPS)], "b": ["y"] * len(IPS)}
        w = encode(tab, schema={"": "cpf"})
        assert w == encode(tab, schema={"": SPEC_CPF})
        assert decode(w) == tab


class TestFailLoud:
    def test_name_desconhecido_lista_o_registry(self):
        with pytest.raises(ValueError, match="desconhecido.*cnpj.*cpf"):
            encode(IPS, schema="zzz")

    def test_posicao_fora_do_range(self):
        with pytest.raises(ValueError, match="fora do range"):
            encode({"a": ["1"]}, schema={3: "ip"})

    def test_colisao_posicao_e_nome_na_mesma_coluna(self):
        with pytest.raises(ValueError, match="DUAS vezes"):
            encode({"a": IPS}, schema={0: "ip", "a": "cpf"})

    def test_canais_antigos_cortados(self):
        # `nature=`/`nature_per_col=` nao existem na assinatura publica: TypeError
        # natural do Python, como qualquer kwarg desconhecido (ADR-0047).
        with pytest.raises(TypeError, match="nature"):
            encode(IPS, nature=SPEC_IP)
        with pytest.raises(TypeError, match="nature_per_col"):
            encode({"a": IPS}, nature_per_col={"a": SPEC_IP})
        with pytest.raises(TypeError, match="nature"):
            decode(encode(IPS), nature=SPEC_IP)

    def test_chave_int_em_entrada_lista(self):
        with pytest.raises(ValueError, match="posicao.*so'.*dict|so' vale pra tabela"):
            encode(IPS, schema={0: "ip"})

    def test_str_escalar_em_tabela_de_2_colunas(self):
        # escalar em tabela de 2+ colunas: qual coluna? informacao necessaria —
        # o erro ensina o caminho (a tabela de UMA coluna aceita: sobrecarga)
        with pytest.raises(ValueError, match="UMA coluna"):
            encode({"a": IPS, "b": ["x"] * len(IPS)}, schema="ip")

    def test_chave_bool_e_tipo_errado(self):
        with pytest.raises(TypeError, match="bool"):
            encode({"a": IPS}, schema={True: "ip"})
        with pytest.raises(TypeError, match="str.*objeto spec"):
            encode({"a": IPS}, schema={"a": 42})
        with pytest.raises(TypeError, match="schema deve ser"):
            encode(IPS, schema=42)


class TestIncrementalESobrecargas:
    """O schema e' INCREMENTAL — default = string semantico, o schema muda um ou
    mais — e tem SOBRECARGA quando o alvo e' inequivoco: tabela/wire de UMA coluna
    aceita a forma escalar."""

    def test_schema_vazio_none_e_col_none_sao_neutros(self):
        tab = {"ip": IPS, "obs": ["x"] * len(IPS)}
        w = encode(tab)
        assert encode(tab, schema={}) == w
        assert encode(tab, schema=None) == w
        assert encode(tab, schema={"ip": None}) == w

    def test_coluna_nao_nomeada_nunca_e_marcada(self):
        tab = {"ip": IPS, "obs": ["x"] * len(IPS)}
        meta = encode(tab, schema={"ip": "ip"}).split("\n", 1)[0]
        assert meta.count(":") == 1 and ":ip" in meta   # SO' a nomeada

    def test_escalar_em_tabela_de_uma_coluna(self):
        # a sobrecarga: sem cerimonia de dict quando o alvo e' inequivoco
        w = encode({"ip": IPS}, schema="ip")
        assert w == encode({"ip": IPS}, schema={"ip": "ip"})
        assert ":ip" in w.split("\n", 1)[0]             # testemunha de APLICACAO
        assert decode(w) == {"ip": IPS}

    def test_escalar_em_dict_aninhado_falha_alto(self):
        # 1 chave mas folha NAO-escalar -> o .8H recusa ensinando (nao ha' silencio)
        with pytest.raises(Exception, match="folha ESCALAR|ESCALAR"):
            encode({"x": {"y": 1}}, schema="cpf")

    def test_decode_escalar_em_wire_de_uma_coluna(self):
        w = encode({"ip": IPS}, schema="ip")
        assert decode(w, schema="ip") == {"ip": IPS}

    def test_decode_escalar_em_wire_multi_ensina(self):
        w = encode({"ip": IPS, "obs": ["x"] * len(IPS)})
        with pytest.raises(ValueError, match="UMA coluna"):
            decode(w, schema="ip")


class TestDecodeSimetrico:
    def test_decode_schema_str_e_posicional(self):
        w = encode({"ip": IPS, "obs": ["x"] * len(IPS)}, schema={"ip": "ip"})
        tab = {"ip": IPS, "obs": ["x"] * len(IPS)}
        # header e' autoritativo; o schema= do decode nao atrapalha o RT
        assert decode(w, schema={"ip": "ip"}) == tab
        assert decode(w, schema={0: "ip"}) == tab

    def test_decode_single_schema_str(self):
        w = encode(IPS, schema="ip")
        assert w.split("\n", 1)[0] == "#TCF.8 :ip"
        assert decode(w, schema="ip") == IPS

    def test_cnpj_pelo_registry(self):
        vals = ["11.222.333/0001-81", "12.ABC.345/01DE-35"] * 10
        w = encode(vals, schema="cnpj")
        assert decode(w) == vals
