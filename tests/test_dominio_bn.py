"""bN de dominio — weld 2026-07-27 (`composicional/dominio_bn.py`, ADR-0036).

Cada teste aqui corresponde a um achado medido nos labs
`experiments/lab/dirty/2026-07/2026-07-27/{1608,1647,2211,2231,2247}`.
"""
from __future__ import annotations

import pytest

from tcf import decode, encode
from tcf.composicional.dominio_bn import (
    BS, DISC_LOTE, DISC_STREAM, MARCADOR, MAX_W, _grafa, _le_grafia, candidatos, dominio,
    valida_payload_b64,
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


class TestGrafiaInjetiva:
    """Bug de CORRUPCAO SILENCIOSA achado pela auditoria adversarial (2026-07-28).

    `_grafa` escapava `"0"` -> `"\\0"` mas devolvia o resto intacto, entao o valor de dado
    que JA' era `"\\0"` saia igual — duas entradas, uma grafia. `encode(['\\0','x']*30)`
    devolvia `['0','x',...]` **sem excecao**, pela API publica, com `list[str]` trivial.
    """

    def test_grafa_e_injetiva(self):
        vals = [None, "0", BS + "0", BS, BS + BS, "x", BS + "x", BS + BS + "0", "00"]
        grafados = [_grafa(v) for v in vals]
        assert len(grafados) == len(set(grafados)), f"colisao: {grafados}"

    def test_le_grafia_e_inversa_exata(self):
        for v in (None, "0", BS + "0", BS, BS + BS, "x", BS + "x", "00", ""):
            assert _le_grafia(_grafa(v)) == v

    @pytest.mark.parametrize("dados", [
        [chr(92) + "0", "x"] * 30,                       # o caso que corrompia
        ["0", chr(92) + "0", "y"] * 20,                  # os dois na MESMA coluna
        [chr(92), chr(92) * 2, "z"] * 20,
        [None, "0", chr(92) + "0"] * 20,                 # + o slot nulo
    ])
    def test_rt_com_backslash_no_dominio(self, dados):
        obtido = decode(encode(dados))
        assert len(obtido) == len(dados)
        assert obtido == dados

    def test_core_ja_preservava(self):
        """Contra-prova: era regressao do bN, nao limitacao do formato."""
        dados = [BS + "0", "x"] * 30
        assert decode(encode(dados, stamp=False)) == dados


class TestCanonicidadeDoCabecalho:
    """O bN violava um invariante que o irmao no MESMO indice 7 ja' travava.

    `int(x, 16)` aceita zero a esquerda, maiuscula, underscore (PEP 515), `0x` e sinal;
    `str.isdigit()` aceita digito Unicode. Familia INFINITA de grafias para o mesmo valor —
    o modo denso rejeita tudo isso desde sempre (`test_typed_singlecol.py`).
    """

    @pytest.mark.parametrize("cab", [
        "#TCF.8B20c8",      # zero a esquerda
        "#TCF.8B200c8",     # dois
        "#TCF.8B2C8",       # hex maiusculo
        "#TCF.8B2c_8",      # underscore (PEP 515)
        "#TCF.8B20xc8",     # prefixo 0x
        "#TCF.8B2+c8",      # sinal
        "#TCF.8B2 c8",      # whitespace
        "#TCF.8B٢c8",  # digito arabe-indico na largura
        "#TCF.8B2c٨",  # digito arabe-indico no hex
        "#TCF.8B9c8",       # largura fora de 1..8
        "#TCF.8B0c8",       # largura 0
    ])
    def test_grafia_nao_canonica_fail_loud(self, cab):
        corpo = encode([f"v{i % 3}" for i in range(200)]).partition("\n")[2]
        with pytest.raises(ValueError):
            decode(cab + "\n" + corpo)

    def test_o_canonico_passa(self):
        dados = [f"v{i % 3}" for i in range(200)]
        w = encode(dados)
        assert w.partition("\n")[0] == "#TCF.8B2c8"
        assert decode(w) == dados


class TestStringVaziaNoDominio:
    """Bug achado pela auditoria adversarial (2026-07-28), achado [5].

    `bloco.rstrip("\\n")` comia TODOS os `\\n` finais, mas o corpo canonico termina em
    EXATAMENTE um. Dominio cujo ULTIMO valor e' a string vazia perdia esse valor, e o
    `decode` estourava com "indice fora do dominio" — RT quebrado pela API publica.
    """

    @pytest.mark.parametrize("dados", [
        ["a", "b", ""] * 40,          # vazia por ULTIMO no dominio: o caso que quebrava
        ["", "a", "b"] * 40,          # vazia primeiro (ja' funcionava)
        ["a", "", "b"] * 40,          # vazia no meio
        ["a", "b", "", "c"] * 30,
        ["", ""] * 30,
    ])
    def test_rt_com_string_vazia(self, dados):
        obtido = decode(encode(dados))
        assert len(obtido) == len(dados)
        assert obtido == dados


class TestNadaDepoisDosBits:
    """Bug achado pela auditoria adversarial (2026-07-28), achado [10].

    Linha extra apos o bloco de bits era IGNORADA calada, enquanto o irmao no mesmo indice 7
    (modo denso) falha alto na mesma sonda. Silencio esconde wire concatenado ou truncado.
    """

    def test_linha_extra_fail_loud(self):
        w = encode([f"v{i % 3}" for i in range(200)])
        with pytest.raises(ValueError):
            decode(w.rstrip("\n") + "\nxxx")

    def test_linha_vazia_final_e_tolerada(self):
        dados = [f"v{i % 3}" for i in range(200)]
        w = encode(dados)
        assert decode(w.rstrip("\n") + "\n") == dados


class TestPayloadB64Canonico:
    """`T-BN-B64-VALIDATE` — lab `2026-08-06-2104` (9 sondas x 5 rotas, 45 celulas).

    Tres checagens, e o lab mostrou que **nenhuma subsome as outras**:

        validate=True        char fora do alfabeto, espaco, padding em lugar errado
        re-codifica+compara  padding a mais, caixa trocada (grafia dupla dos MESMOS bytes)
        tamanho exato        extensao com bytes ZERO, truncamento

    O `_decode_denso` ja' fazia as tres; o `decode_bn` nao fazia nenhuma e o
    `_decode_lazy_bool` fazia so' a primeira.
    """

    #: as tres rotas que carregam payload base64, e como achar o payload em cada wire
    ROTAS = {
        "bn-B": [f"v{i % 3}" for i in range(200)],
        "denso-b1": [bool(i % 2) for i in range(200)],
        "denso-b2": [None if i % 3 == 0 else bool(i % 2) for i in range(200)],
        "lazy-bB": [None if i % 7 == 0 else ([True, False][i % 2] if i % 3 else f"x{i % 4}")
                    for i in range(200)],
    }

    @staticmethod
    def _muta(wire, fn):
        """Aplica `fn` ao payload b64, seja ele apos `=` (bN/lazy) ou na ultima linha."""
        ls = wire.rstrip("\n").split("\n")
        i = next((j for j, l in enumerate(ls) if l.startswith("=")), len(ls) - 1)
        pre = "=" if ls[i].startswith("=") else ""
        ls[i] = pre + fn(ls[i][len(pre):])
        return "\n".join(ls) + "\n"

    @pytest.mark.parametrize("rota", list(ROTAS))
    @pytest.mark.parametrize("nome,mut", [
        ("char-invalido", lambda p: p[:5] + "!" + p[5:]),
        ("espaco", lambda p: p[:5] + " " + p[5:]),
        ("quatro-invalidos", lambda p: p[:5] + "!!!!" + p[5:]),
        ("padding-extra", lambda p: p.rstrip("=") + "=="),
        ("truncado", lambda p: p[:-4]),
        # A sonda que o lab ANTERIOR nao tinha: bytes ZERO em base64 CANONICO.
        # Atravessa o `validate` E a checagem de bits-de-padding do `unpack_w`.
        ("extensao-zero", lambda p: p.rstrip("=") + "AAAA"),
    ])
    def test_payload_adulterado_falha_alto(self, rota, nome, mut):
        dados = self.ROTAS[rota]
        with pytest.raises(ValueError) as exc:
            decode(self._muta(encode(dados), mut))
        assert "#TCF.8" in str(exc.value), f"mensagem sem nivel TCF: {exc.value}"

    @pytest.mark.parametrize("rota", list(ROTAS))
    def test_wire_valido_continua_passando(self, rota):
        """Byte-neutro: a validacao so' toca caminho de erro."""
        dados = self.ROTAS[rota]
        assert decode(encode(dados)) == dados

    def test_as_tres_checagens_sao_independentes(self):
        """Nenhuma subsome as outras — foi o que fechou a discussao de "opcional"."""
        import base64 as _b64

        raw = bytes(range(25))
        canon = _b64.b64encode(raw).decode().rstrip("=")
        n, w = 200, 1                                    # 200*1/8 = 25 bytes

        def _classes(payload):
            try:
                valida_payload_b64(payload, n, w, "#TCF.8B")
                return "passa"
            except ValueError as e:
                return str(e)

        # so' o validate pega
        assert "nao e' base64" in _classes(canon[:5] + "!" + canon[5:])
        # so' a re-codificacao pega (bytes validos, grafia dupla)
        assert "nao-canonico" in _classes(canon + "==")
        # so' o tamanho pega (base64 canonico, bytes ZERO a mais)
        assert "esperado 25" in _classes(canon + "AAAA")
        # o canonico passa
        assert _classes(canon) == "passa"

    def test_mensagem_e_de_nivel_tcf_nas_tres_rotas(self):
        """O buraco original: o bN vazava `binascii.Error` cru."""
        for rota, dados in self.ROTAS.items():
            mut = self._muta(encode(dados), lambda p: p[:5] + "!" + p[5:])
            with pytest.raises(ValueError) as exc:
                decode(mut)
            assert "payload" in str(exc.value), f"{rota}: {exc.value}"


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
