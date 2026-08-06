"""Weld #4 — single-col TIPADO (#TCF.8<tag>). Decode = pre-avaliador de apelidos.

#4a (este arquivo, decode): o decode passa a aceitar `#TCF.8<tag>\n<corpo-core>` (modo CORE), expande
pro corpo core (reusa `_decode_column`) e casta pro tipo. A variavel `modo` (o conceito do `~`) e'
deduzida da POSICAO (indice 7) — NAO ha `~` no wire. Modo denso bN soldado p/ bool: b1 (1 bit,
sem null, #4b) e b2 (2 bits, ternario com null, weld 2026-07-31, ADR-0037).

Nota de design (owner 2026-07-24): a funcao e' acionada pela VARIAVEL, nao pelo caractere; o `~` e'
categoria 4 (nunca byte de wire, so' nome interno). Ver notas 2026-07-24-0100/0322.
"""
import pytest

from tcf import encode, decode


def _typed_core_wire(vals, tag, render):
    """Constroi um wire tipado-core a mao: '#TCF.8<tag>\n' + corpo core dos literais renderizados."""
    # stamp=False: aqui o encode e' usado so' pra gerar o CORPO — o header do wire tipado
    # e' o `#TCF.8<tag>` construido logo abaixo (ADR-0034: header e' do artefato, 1 so').
    body = encode([render(v) for v in vals], stamp=False) if vals else ""
    return f"#TCF.8{tag}\n{body}"


class TestTypedSingleColDecode:
    def test_bool_core_roundtrip(self):
        for vals in ([True, False, True, True], [True] * 5, [False] * 3,
                     [bool(i % 2) for i in range(10)], [True], [False]):
            w = _typed_core_wire(vals, "b", lambda v: "true" if v else "false")
            back = decode(w)
            assert back == vals and all(isinstance(x, bool) for x in back), (vals, back)

    def test_n_e_s_decodam(self):
        """2026-07-25: `n` (numero) passou a ser EMITIDO; `s` (string) decoda mas o encoder
        NAO emite — string e' o tipo implicito por exclusao (camada 1 do ADR-0029). Aceitar
        `#TCF.8s` fecha a coerencia do modelo: todo mecanismo aceita a forma explicita."""
        # NOTA: no corpo, digito NU e' REFERENCIA DE FRAGMENTO — o literal `1` se escreve `\1`.
        # Por isso todo numero paga +1 B de escape sob a tag `n` (registrado no lab 1746).
        assert decode("#TCF.8n\n\\1\n\\2\n\\3\n") == [1, 2, 3]
        assert decode("#TCF.8s\nfoo\nbar\n") == ["foo", "bar"]
        assert not encode(["foo", "bar"]).startswith("#TCF.8s")   # encoder nao emite `s`

    def test_tag_fora_do_namespace_fail_loud(self):
        # digito NAO entra: '#TCF.81' e' lido como VERSAO 81, outro ramo de fail-loud (ADR-0032)
        for tag in ("z", "x", "Q"):
            with pytest.raises(ValueError, match="desconhecido"):
                decode(f"#TCF.8{tag}\nfoo\n")

    def test_n_fora_do_dominio_fail_loud(self):
        with pytest.raises(ValueError, match="dominio numerico"):
            decode("#TCF.8n\nabc\n")

    def test_n_nao_aceita_nan_inf(self):
        """Simetria: o encoder recusa NaN/±Inf (RFC 8259), entao o decode tambem."""
        for lit in ("nan", "inf", "-inf", "Infinity"):
            with pytest.raises(ValueError, match="RFC 8259|dominio numerico"):
                decode(f"#TCF.8n\n{lit}\n")

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

    def test_numero_vira_tag_n(self):
        """2026-07-25: int/float sairam do `.8H` e ganharam a tag `n` (mesma generalizacao)."""
        assert encode([1, 2, 3]).startswith("#TCF.8n\n")
        # o sufixo de POLARIDADE (weld 2026-07-26) e' opcional e entra DEPOIS da tag:
        # `#TCF.8n`, `#TCF.8n!` ou `#TCF.8n!!`. A tag continua sendo o indice 6.
        assert encode([1.5, 2.0]).split("\n")[0].startswith("#TCF.8n")
        assert decode(encode([1, 2, 3])) == [1, 2, 3]
        assert decode(encode([1.5, 2.0])) == [1.5, 2.0]

    def test_int_vs_float_preservado(self):
        """A tag e' uma so' (`n`, como no JSON), entao o RT precisa distinguir pela GRAFIA."""
        for v in ([1, 2], [1.0, 2.0], [1, 2.5], [-0.0], [10 ** 25], [1e100]):
            volta = decode(encode(v))
            assert volta == v and [type(x) for x in volta] == [type(x) for x in v], v

    def test_nan_inf_seguem_fail_loud(self):
        """NaN/±Inf ficam FORA do JSON (RFC 8259) — nao entram na rota tipada."""
        for v in ([float("nan")], [float("inf")], [1.0, float("-inf")]):
            with pytest.raises(Exception, match="NaN|Infinity"):
                encode(v)

    def test_str_e_mixed_inalterados(self):
        # str -> single-col NAO-tipado: version-stamp puro, sem tag de tipo no indice 6
        assert encode(["a", "b"]).startswith("#TCF.8\n")
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


class TestTiposInternosFonteUnica:
    """`src/tcf/tipos_internos.py` e' a FONTE UNICA das tabelas congeladas bool (2026-08-01).
    As tabelas sao CONTRATO DE FORMATO — se mudarem aqui, o wire muda; o teste pincha."""

    def test_tabelas_congeladas(self):
        from tcf.tipos_internos import TABELA_B1, TABELA_B2
        assert TABELA_B1 == (False, True)
        assert TABELA_B2 == (None, False, True)

    def test_render_cabe_no_cast(self):
        # tudo que o encoder EMITE, o decode tem de CASTAR (e com identidade de valor)
        from tcf.tipos_internos import CAST_B, RENDER_B
        assert set(RENDER_B.values()) <= set(CAST_B)
        for v in (False, True):
            assert CAST_B[RENDER_B[v]] is v

    def test_slots_sao_os_da_tabela_b2(self):
        # RENDER_B e' a projecao valor->grafia da MESMA tabela do denso b2 (ADR-0037/0038)
        from tcf.tipos_internos import RENDER_B, TABELA_B2
        assert RENDER_B[False] == str(TABELA_B2.index(False))
        assert RENDER_B[True] == str(TABELA_B2.index(True))


class TestTipadoBoolIndiceDefault:
    """Render em SLOTS default da tag `b` (weld 2026-08-01, ADR-0038): o core grafava
    `true`/`false` como NOMES; agora grafa os slots da MESMA tabela do denso b2
    (null=0/false=1/true=2). Nomes seguem DECODAVEIS-nao-emitidos (contrato do modo `C`,
    ADR-0036). Medicao: lab 2026-08-01-0037-tipado-bool-indice-default."""

    def test_rt_estrito_valor_e_tipo(self):
        casos = [
            [True] * 200,                                       # constante (core/RLE)
            [True] * 100 + [None] + [False] * 99,               # run-heavy ternario
            [True] * 50 + [False] * 50 + [True] * 50 + [False] * 50,   # runs-4
            [bool(i % 2) for i in range(200)],                  # alternado (b1)
            [None if i % 3 == 0 else bool(i % 2) for i in range(200)], # ternario (b2)
            [True] * 3, [True, None, False],                    # tiny-n
        ]
        for vals in casos:
            back = decode(encode(vals))
            assert len(back) == len(vals)
            assert back == vals
            assert all(type(a) is type(b) for a, b in zip(back, vals))

    def test_pin_observavel_constante(self):
        # o caso-motivacao: '*200|true' (18 B) -> '*200|\2' (16 B)
        w = encode([True] * 200)
        assert w == "#TCF.8b\n*200|\\2\n"
        assert len(w.encode()) == 16

    def test_core_grafa_slots_no_run_heavy(self):
        # onde o core VENCE o b2: o corpo tem de vir em slots \2/\1, nao em nomes
        vals = [True] * 100 + [None] + [False] * 99
        w = encode(vals)
        assert w[7:8] == "\n"                                     # modo core vence
        assert "\\2" in w and "\\1" in w and "true" not in w and "false" not in w
        assert decode(w) == vals

    def test_legado_nomes_decodaveis(self):
        # contrato decodavel-NAO-emitido (modo `C`, ADR-0036): wires antigos por nomes leem
        assert decode("#TCF.8b\ntrue\nfalse\n^1\n") == [True, False, True]

    def test_slots_fora_do_dominio_fail_loud(self):
        # \0 colide com o slot do null; \3 e' o reservado do b2; \15 esta' fora
        for lit in ("\\0", "\\3", "\\15"):
            with pytest.raises(ValueError, match="dominio bool"):
                decode(f"#TCF.8b\n{lit}\n")

    def test_floor_por_regime(self):
        # FLOOR inalterado: sem null -> b1; com null -> b2; run-heavy -> core com slots
        assert encode([bool(i % 2) for i in range(64)])[7:8] == "1"
        assert encode([None if i % 3 == 0 else bool(i % 2) for i in range(200)])[7:8] == "2"
        assert encode([True] * 100 + [None] + [False] * 99)[7:8] == "\n"

    def test_deterministico(self):
        vals = [True] * 100 + [None] + [False] * 99
        assert encode(vals) == encode(vals)


class TestBoolDensoB2Ternario:
    """Denso b2 (weld 2026-07-31, ADR-0037): bool COM null a 2 bits/elem, dominio implicito
    CONGELADO null=0/false=1/true=2 (3 = reservado). Medido no lab 2026-07-31-2350:
    546 B (core) -> 79 B p/ n=200, vence ate' n=3."""

    def test_rt_estrito_ternario(self):
        # RT estrito: valor E tipo (True/False/None) E comprimento
        casos = [
            [None, False, True],
            [None, False, None, False],                        # {null,false}
            [None, True, None, True, True],                    # {null,true}
            [None if i % 3 == 0 else bool(i % 2) for i in range(200)],
            [None if i % 17 == 0 else bool(i % 2) for i in range(200)],
            [None if i % 3 == 0 else bool(i % 2) for i in range(1000)],
        ]
        for vals in casos:
            back = decode(encode(vals))
            assert len(back) == len(vals)
            assert back == vals
            assert all(type(a) is type(b) for a, b in zip(back, vals))

    def test_emite_modo_b2_quando_vence(self):
        # ternario misto -> modo '2' no indice 7; header '#TCF.8b2<n-hex>'
        vals = [None if i % 3 == 0 else bool(i % 2) for i in range(200)]
        w = encode(vals)
        assert w.startswith("#TCF.8b2c8\n")                      # n=200='c8' em hex
        assert len(w.encode()) == 79                             # medido no lab (546 do core)

    def test_floor_bool_puro_sempre_b1_nunca_b2(self):
        # FLOOR nunca-pior: SEM null o b1 (1 bit) domina o b2 (2 bits) — modo '1' ou core
        for vals in ([bool(i % 2) for i in range(64)], [True] * 64, [False] * 3):
            w = encode(vals)
            assert w[7:8] in ("\n", "1"), w[:16]                 # core ou b1 — NUNCA b2

    def test_b2_so_com_null_e_quando_vence(self):
        # run ternario longo (RLE esmaga) -> core pode vencer; o FLOOR decide por tamanho
        vals = [None if i % 3 == 0 else bool(i % 2) for i in range(200)]
        assert encode(vals)[7:8] == "2"
        core_so = "#TCF.8b\n" + encode(
            [None if x is None else ("true" if x else "false") for x in vals],
            stamp=False).split("\n", 1)[1]
        assert len(encode(vals).encode()) <= len(core_so.encode())

    def test_simbolo_3_reservado_fail_loud(self):
        # simbolo 3 = RESERVADO no dominio ternario -> fail-loud (wire adulterado)
        from tcf.bitpack import pack_w
        import base64 as b64mod
        payload = b64mod.b64encode(pack_w([0, 1, 2, 3], 2)).decode("ascii")
        with pytest.raises(ValueError, match="simbolo 3|reservado|adulterado"):
            decode(f"#TCF.8b24\n{payload}")

    def test_b2_adulterado_fail_loud(self):
        vals = [None if i % 3 == 0 else bool(i % 2) for i in range(200)]
        w = encode(vals)
        head, _, b64 = w.partition("\n")
        with pytest.raises(ValueError, match="payload"):
            decode(head + "\n" + b64[:-4])                       # payload truncado
        with pytest.raises(ValueError, match="base64"):
            decode(head + "\n!" + b64[1:])                       # b64 nao-canonico

    def test_b2_header_nao_canonico_fail_loud(self):
        # mesma canonicidade hex do b1: '0c8' (zero a esquerda) NAO colide com 'c8'
        vals = [None if i % 3 == 0 else bool(i % 2) for i in range(200)]
        w = encode(vals)
        head, body = w.split("\n", 1)
        assert head == "#TCF.8b2c8"
        with pytest.raises(ValueError, match="invalido"):
            decode("#TCF.8b20c8\n" + body)

    def test_b2_deterministico(self):
        # canonicidade: mesmo input -> mesmo wire, byte a byte
        vals = [None if i % 3 == 0 else bool(i % 2) for i in range(200)]
        assert encode(vals) == encode(vals)

    def test_largura_fora_de_12_fail_loud(self):
        # w=4/8 continuam invalidos p/ bool (namespace reservado)
        with pytest.raises(ValueError, match="largura|invalid"):
            decode("#TCF.8b42\nAAAA")


class TestDensoHexN:
    """`n` do modo denso em HEX (owner 2026-07-24): len(hex(n))<=len(dec(n)) p/ todo n>=0 -> nunca
    pior, O(1), sem custo de ambiguidade (parse posicional: modo sempre 1o char)."""

    def test_n_e_hex_no_wire(self):
        assert encode([bool(i % 2) for i in range(255)]).split("\n", 1)[0].endswith("ff")
        assert encode([bool(i % 2) for i in range(256)]).split("\n", 1)[0].endswith("100")

    def test_rt_fronteiras_hex(self):
        for n in (1, 9, 10, 15, 16, 63, 64, 65, 100, 255, 256, 1000, 4095, 4096):
            v = [bool(i % 2) for i in range(n)]
            assert decode(encode(v)) == v

    def test_grafia_nao_canonica_fail_loud(self):
        # canonicidade: '0a' (zero a esquerda) tem que FALHAR, nao colidir com 'a' (mesma classe do
        # weld #2/LF — duas grafias, mesmo valor, violaria S1.2)
        w = encode([bool(i % 2) for i in range(10)])              # wire canonico com n='a'
        head, body = w.split("\n", 1)
        assert head.endswith("a") and not head.endswith("0a")
        nao_canonico = head[:-1] + "0a" + "\n" + body
        with pytest.raises(ValueError, match="invalido"):
            decode(nao_canonico)


class TestLazyBool:
    """Lazy bool `#TCF.8bB<w><n>` (ADR-0039; labs 2026-08-01-0229 / -0322-fiacao-rota-real).

    Uniao bool+str(+null) — hoje fail-loud no `.8H` — passa a ter rota propria: cabeca
    CONGELADA implicita null=0/false=1/true=2 (TABELA_B2) + extras str declarados a partir
    do slot 3, por 1a aparicao. Contrato UNIAO: decode devolve lista mista [bool|None|str].
    """

    def _rt_estrito(self, vals):
        w = encode(vals)
        assert w.startswith("#TCF.8bB")
        back = decode(w)
        assert back == vals
        assert all(type(a) is type(b) for a, b in zip(back, vals))   # tipo-estrito
        return back

    # ---- RT tipo-estrito ----
    def test_rt_raro_e_frequentes(self):
        self._rt_estrito([True, "other", None, False] * 50)                       # raro
        self._rt_estrito([True, "other", False, "other", None, "other"] * 34)     # frequentes

    def test_rt_k_extras(self):
        for k in (1, 5, 20):
            vals = [True, None, False] + [f"e{i}" for i in range(k)]
            self._rt_estrito(vals * 10)

    def test_rt_armadilha_tipos(self):
        """Extras que se CONFUNDIRIAM com a cabeca se o decode pos-mapeasse nomes:
        'true'/'false'/'0'/'1' sao STRINGS e voltam strings — nunca bool/None."""
        vals = [True, "true", None, "0", False, "1", "false"] * 20
        back = self._rt_estrito(vals)
        assert back[1] == "true" and type(back[1]) is str
        assert back[0] is True and back[2] is None and back[4] is False

    def test_rt_extra_vazio(self):
        """Extra '' e' VALIDO: o dominio e' a linha vazia invisivel (bugfix `[:-1]` do bn)."""
        self._rt_estrito([True, "", None, False, True])

    def test_rt_ns(self):
        for n in (3, 200, 1000):
            vals = [True, "x", None, False][:(n % 4) or 4] * (n // 4 + 1)
            self._rt_estrito(vals[:n])

    # ---- Deteccao (quem NAO entra na rota) ----
    def test_str_null_sem_bool_vai_flat(self):
        w = encode([None, "x", "y", None])
        assert "bB" not in w and decode(w) == [None, "x", "y", None]   # flat com slot 0

    def test_bool_puro_intocado(self):
        assert encode([True, False, True]).startswith("#TCF.8b1")       # b1
        assert encode([True, None, False]).startswith("#TCF.8b2")       # b2 ternario

    def test_bool_str_int_fail_loud(self):
        from tcf.hierarchical import HierarchicalError
        with pytest.raises(HierarchicalError):
            encode([True, "x", 1])

    def test_lf_em_extra_fail_loud(self):
        """Achado da fiacao 0322: `_encode_column` devolve LF CALADO — o lazy recusa-se a
        oferecer (None) e a uniao cai no fail-loud do `.8H`."""
        from tcf.hierarchical import HierarchicalError
        with pytest.raises(HierarchicalError):
            encode([True, "a\nb", False])

    def test_w_maior_que_8_fail_loud(self):
        from tcf.hierarchical import HierarchicalError
        with pytest.raises(HierarchicalError):
            encode([True] + [f"e{i}" for i in range(254)])              # 3+254 > 256

    # ---- Decode ----
    def test_bn_flat_intocado(self):
        """`#TCF.8B…` (dominio bn da rota FLAT, ADR-0036) segue devolvendo STRINGS."""
        from tcf.composicional.dominio_bn import candidatos
        from tcf.encoder import _encode_column
        vals = ["a", "b", "a", "c", "a", "b"]
        wires = candidatos(vals, lambda vs: _encode_column(vs, header="val"), None)
        assert wires and wires[0].startswith("#TCF.8B")
        back = decode(wires[0])
        assert back == vals and all(type(x) is str for x in back)

    def test_dominio_redeclarando_cabeca_fail_loud(self):
        """`0` cru no dominio = slot 0 (null) redeclarado — a cabeca 0/1/2 e' implicita e
        NUNCA se declara (check da fiacao 0322)."""
        with pytest.raises(ValueError, match="redeclara"):
            decode("#TCF.8bB24\n0\n=sQ")

    def test_indice_fora_da_tabela_fail_loud(self):
        # tabela = 3 cabeca + 1 extra ('x') = 4 valores; o payload carrega o indice 4
        # (craftado: pack_w([4], 3) -> 'gA') -> fail-loud, nunca corrompe em silencio.
        with pytest.raises(ValueError, match="fora da tabela"):
            decode("#TCF.8bB31\nx\n=gA")
        # sem dominio algum (bloco vazio le como o extra ''): indice 3 = extra '',
        # entao aqui o que falha e' a tabela curta demais p/ o indice da cabeca? Nao —
        # bloco vazio E' o extra '' valido; wire minimo '#TCF.8bB24\n=sQ' decoda
        # [True, '', None, False]. Quem falha e' indice alto em tabela curta (acima).

    def test_header_nao_canonico_fail_loud(self):
        with pytest.raises(ValueError, match="largura"):
            decode("#TCF.8bB04\nx\n=sQ")          # w com zero a esquerda / fora de 1..8
        with pytest.raises(ValueError, match="contagem"):
            decode("#TCF.8bB204\nx\n=sQ")         # n com zero a esquerda
        with pytest.raises(ValueError, match="contagem"):
            decode("#TCF.8bB2zz\nx\n=sQ")         # n nao-hex

    def test_trailing_e_marcador_fail_loud(self):
        with pytest.raises(ValueError, match="apos o bloco"):
            decode("#TCF.8bB24\ntrue\n=sQ\nlixo")
        with pytest.raises(ValueError, match="marcador"):
            decode("#TCF.8bB24\ntrue\nsQ")

    def test_n_s_com_B_fail_loud(self):
        """Lazy numerico/string e' OUTRO ticket: `nB`/`sB` caem no fail-loud de header."""
        with pytest.raises(ValueError, match="invalido"):
            decode("#TCF.8nB24\nx\n=sQ")

    # ---- Determinismo + pin byte-exato ----
    def test_determinismo(self):
        vals = [True, "other", None, False] * 50
        assert encode(vals) == encode(vals)

    def test_pin_byte_exato_lab_0322(self):
        """Pin byte-exato do wire de referencia do lab 2026-08-01-0322
        (outputs/extra-true-lazy.tcf): [True,'true',None,False] -> 19 B."""
        assert encode([True, "true", None, False]) == "#TCF.8bB24\ntrue\n=sQ"
        assert encode([True, "", None, False, True]) == "#TCF.8bB25\n\n=sYA"
