"""T-QA-8 F0 lote 1 — repros pinados dos BUG-01/02/07 (red->green, 2026-07-10).

Decisões do owner (2026-07-10):
- BUG-01: coluna com nome '' = coluna SEM nome (anônima) — a entrada é TRANSFORMADA
  na fronteira (warning), o meta NUNCA emite escape-vazio; no decode, escape/declaração
  de nome vazio = ERRO (marcador de corrupção; futuro reparador em ticket próprio).
  ⚠ SUPERADA em 2026-08-21 (ADR-0046): '' passou a ser nome VAZIO, emitido como `\z`
  (a grafia que o .8H já usava desde ADR-0033) e preservado no decode — era o único
  caso em que o TCF alterava o dado (BUG-CHAVE-VAZIA-POSICIONAL). O sentinela de
  corrupção continua: '<size>=' com token CRU vazio é erro. Pins re-escritos abaixo.
- BUG-02: paridade view vs decode por CONSTRUÇÃO (parser único do meta), não por
  verificação extra.
- BUG-07: `body_bytes` MANTÉM a semântica de candidato TCF (custo de compute/memória —
  telemetria válida nesse sentido); os bytes REALMENTE emitidos + modo vencedor são
  capturados NO PONTO do min() (contagem já existente pro header — zero passada extra).
"""

from __future__ import annotations

import warnings

import pytest

from tcf import decode, encode, view
from tcf.side_outputs import SideOutputs

# Colunas de controle com modo PREVISÍVEL no min(tcf, raw, dict, split):
VALS_RAW = ["q", "w", "e"]  # curtas/únicas -> raw vence
VALS_DICT = ["alpha", "beta"] * 50  # K=2, N=100 -> dict vence
VALS_TCF = ["constante-longa-repetida-x"] * 20  # RLE *20| -> tcf vence


# ---------------------------------------------------------------------------
# BUG-01 — nome de coluna vazio '' (encode: transforma; decode: fail-loud)
# ---------------------------------------------------------------------------


class TestBug01EmptyColName:
    # RE-PIN 2026-08-21 (ADR-0046): os quatro testes abaixo pinavam a decisão de
    # 2026-07-10 ('' -> anônima + warning + guard de colisão). Ela foi SUPERADA: ''
    # agora é nome VAZIO, emitido como `\z` e preservado. Cada teste diz o que ERA
    # e o que passou a ser — o traço fica, a superfície muda (Strata §3).

    def test_empty_name_is_preserved_no_warning(self):
        # ERA: '' virava anônima com UserWarning e decodava '0'.
        table = {"": ["x", "y"], "b": ["p", "q"]}
        with warnings.catch_warnings():
            warnings.simplefilter("error")          # NENHUM warning agora
            blob = encode(table)
        assert decode(blob) == table                # RT exato: '' volta ''
        _parity(blob)

    def test_empty_name_single_column_table(self):
        # ERA: {'0': ['a', 'b']}.
        blob = encode({"": ["a", "b"]})
        assert blob.split("\n", 1)[0] == "#TCF.8M!\\z"
        assert decode(blob) == {"": ["a", "b"]}

    def test_empty_name_meta_uses_z_sentinel(self):
        # ERA: "nenhum '\' no meta" (a transformação EVITAVA o escape). AGORA o meta
        # carrega exatamente `\z` — o sentinela do .8H (ADR-0033), inemitível por dado.
        blob = encode({"": ["x", "y"], "b": ["p", "q"]})
        meta = blob.split("\n", 1)[0]
        assert "=\\z" in meta                       # '' não-última: '<size>=\z'
        # e um nome LITERAL '\z' sai com a barra dobrada — não colide
        blob2 = encode({"\\z": ["x", "y"], "b": ["p", "q"]})
        assert "=\\\\z" in blob2.split("\n", 1)[0]
        assert decode(blob2) == {"\\z": ["x", "y"], "b": ["p", "q"]}

    def test_empty_name_and_column_zero_are_distinct_names(self):
        # ERA: ValueError de colisão ('' viraria '0' e colidiria com a coluna real '0').
        # AGORA '' e '0' são dois nomes distintos — nada a colidir.
        table = {"": ["x"], "0": ["y"]}
        blob = encode(table)
        assert decode(blob) == table
        _parity(blob)

    def test_decode_escaped_dangling_backslash_is_error(self):
        # nome terminando em backslash SOLTO (cauda ímpar = escape de nada): o
        # encoder nunca emite ('\' legítimo sai '\\', cauda par) -> corrupção.
        # Obs: '\,' NÃO é erro (vírgula escapada legítima de um nome com ',').
        corrupt = "#TCF.8M!1=b,a\\\nxy"  # último token: 'a\' (dangling)
        with pytest.raises(ValueError, match="corromp|dangling|solto"):
            decode(corrupt)

    def test_decode_declared_empty_name_is_error(self):
        # '<size>=' (nome DECLARADO mas vazio): encoder nunca emite -> corrupção
        corrupt = "#TCF.8M1=,!b\nxy"
        with pytest.raises(ValueError, match="corrup|vazio"):
            decode(corrupt)


class TestMetaColisaoNomePosicional:
    """T-META-COLISAO-NOME-POSICIONAL (2026-08-16) — decode de wire ESTRANGEIRO.

    Nome explícito que casa com o nome POSICIONAL de uma coluna anônima: as duas
    resolvem para a mesma chave. O `decode` devolvia MENOS colunas do que o header
    declara (a 2ª sobrescreve a 1ª no dict) e a `view` servia os MESMOS bytes em duas
    chaves — nos dois casos CALADO. Os cheques do BUG-05 não pegam: bytes e n_rows
    fecham.

    O ENCODE nunca emite esta forma (chaves de dict são únicas; `''` tem guard próprio
    em `multi/core.py:316-326`; `drop_names` torna TODAS posicionais e distintas) —
    por isso o repro é wire escrito à mão.
    """

    # anônima na posição 0 (decoda '0') + coluna NOMEADA '0'; 3 valores por coluna
    _C0, _C1, _C2 = "x\ny\nz", "a\nb\nc", "f\ni\nm"
    WIRE = (
        f"#TCF.8M!{len(_C0.encode()):x},!{len(_C1.encode()):x}=0,!fim\n{_C0}{_C1}{_C2}"
    )

    def test_decode_colisao_posicional_fail_loud(self):
        with pytest.raises(ValueError, match="repetid|colis|posicional"):
            decode(self.WIRE)

    def test_view_colisao_posicional_fail_loud(self):
        # a view falhava PIOR que o decode: reportava as 3 colunas e servia os
        # bytes da 2ª nas duas chaves '0' (contagem não denunciava)
        with pytest.raises(ValueError, match="repetid|colis|posicional"):
            view(self.WIRE)

    def test_encode_legitimo_nao_dispara_o_guard(self):
        # contra-prova: o guard NÃO pode incomodar wire que o encoder emite
        vals = [f"v{i}" for i in range(4)]
        for blob in (
            encode({"a": vals, "b": vals, "c": vals}),
            encode({"a": vals, "b": vals}, drop_names=True),
            encode({"a": vals, "b": vals}, min_header=False),
            encode({"0": vals, "1": vals}),          # nomes numéricos EXPLÍCITOS, sem anônima
        ):
            decode(blob)
            view(blob)


class TestPolaridadeComeNome:
    """T-POLARIDADE-COME-NOME (fechado 2026-08-16, item C1) — RT quebrado CALADO.

    A polaridade é camada de BORDA, a primeira coisa do decode: rodava
    `_separa_sufixo_polaridade(line1[6:])` em TODO wire `#TCF.8`. No `.8M` esse
    `line1[6:]` é `M<meta>`, e o fim do meta é o NOME DA ÚLTIMA COLUNA (forma
    `min_header`) — então `#TCF.8Mobs.` separava `('Mobs', '.')` e a coluna decodava
    como `obs`. Com pontuação dobrada, os VALORES também corrompiam. 48/64 nomes no
    `.8M`, 38/64 no `.8H`, **zero warnings**.

    FIX (opção B, aprovada pelo owner): escopo de discriminador — o pré-passe não age
    em `M`/`H`. O encode NUNCA polariza essas rotas (`encoder.py:489` declara, e os 3
    sítios de `polariza()` são single-col), logo o pré-passe ali só podia errar.
    **Custo em bytes: zero** — nada muda no que o encode emite.
    """

    VALS = [f"v{i}" for i in range(26)]

    @pytest.mark.parametrize(
        "nome", ["obs.", "obs..", "ab!", "ab!!", "qtd.", ".", "..", "a.", "valor_r$", "id#"]
    )
    def test_nome_terminado_em_pontuacao_faz_rt(self, nome):
        d = {nome: list(self.VALS)}
        assert decode(encode(d)) == d, "a chave e/ou os valores voltaram diferentes"

    @pytest.mark.parametrize("nome", ["obs.", "ab!!", "."])
    def test_mesma_coisa_no_8h(self, nome):
        recs = [{nome: v} for v in self.VALS]
        assert decode(encode(recs)) == recs

    def test_sweep_pontuacao_ascii_completo(self):
        # o sweep que media 48/64 e 38/64 quebrados: agora tem de ser 0
        import string

        for p in string.punctuation:
            for nome in (f"ab{p}", f"ab{p}{p}"):
                d = {nome: list(self.VALS)}
                assert decode(encode(d)) == d, f".8M quebrou em {nome!r}"
                recs = [{nome: v} for v in self.VALS]
                assert decode(encode(recs)) == recs, f".8H quebrou em {nome!r}"

    def test_single_col_polarizado_nao_regride(self):
        # CONTRA-PROVA: as rotas que USAM a polaridade de verdade não podem mudar
        from tcf.decoder import _separa_sufixo_polaridade as _sep

        casos = [
            [f"{i:02d}.{i:02d}-{i:03d}" for i in range(30)],   # flat -> '#TCF.8!'
            [i + 0.5 for i in range(30)],                       # tipado -> '#TCF.8n!!'
        ]
        for vals in casos:
            blob = encode(vals)
            _tag, suf = _sep(blob.split("\n", 1)[0][6:])
            assert suf, "pré-condição: este caso DEVE ser polarizado"
            assert decode(blob) == vals

    def test_encode_nunca_polariza_m_ou_h(self):
        # a PREMISSA do fix: se o encode polarizasse M/H, ignorar o sufixo perderia dado
        from tcf.decoder import _separa_sufixo_polaridade as _sep

        cols = {
            "a": [f"{i:02d}.{i:02d}-{i:03d}" for i in range(8)],   # atrai polaridade
            "b": [str(i) for i in range(8)],
        }
        for dado in (cols, [dict(zip(cols, t)) for t in zip(*cols.values())]):
            line1 = encode(dado).split("\n", 1)[0]
            assert line1[6:7] in ("M", "H"), "pré-condição: rota M/H"
            assert _sep(line1[6:]) == ("", ""), "encode NÃO deve polarizar M/H"


class TestAnonLastColGrammar:
    """Achado da verificação adversarial F0 (2026-07-10): '<size>' bare no ÚLTIMO
    token é ambíguo com NOME (0xc parsearia como coluna 'c') -> última anônima
    emite SEMPRE sem size, inclusive com min_header=False."""

    def test_min_header_false_empty_name_last_no_key_corruption(self):
        # repro do refutador: size hex da anônima colidia com o nome 'c' e a
        # tabela decodava com UMA coluna só (dados perdidos)
        # RE-PIN 2026-08-21 (ADR-0046): '' não é mais anônima — é nome VAZIO e sai
        # `<size>=\z` com min_header=False; o RT é exato. A ambiguidade original
        # (size bare no último token) segue coberta pelo teste de drop_names abaixo.
        table = {"c": ["k1", "k2", "k3", "k4"], "": ["abc", "de", "fg", "hi"]}
        blob = encode(table, min_header=False)
        assert decode(blob) == table
        _parity(blob)

    def test_min_header_false_drop_names_all_positional(self):
        vals = [f"item_{i:03d}_end" for i in range(4)]
        table = {"a": vals, "b": ["1", "2", "3", "4"], "c": vals}
        blob = encode(table, drop_names=True, min_header=False)
        assert list(decode(blob).keys()) == ["0", "1", "2"]
        _parity(blob)

    def test_empty_name_with_drop_names_has_no_false_collision(self):
        # com drop_names TODAS decodam posicionais — '1' de entrada não colide.
        # RE-PIN 2026-08-21 (ADR-0046): sem warning — '' é dropado como qualquer
        # outro nome quando o chamador pede drop_names (o posicional é o pedido,
        # não uma mutação).
        blob = encode({"1": ["a", "b"], "": ["c", "d"]}, drop_names=True)
        assert decode(blob) == {"0": ["a", "b"], "1": ["c", "d"]}


# ---------------------------------------------------------------------------
# BUG-02 — paridade view vs decode (parser único)
# ---------------------------------------------------------------------------


def _parity(blob: str):
    """view e decode devem enxergar as MESMAS colunas com os MESMOS valores."""
    dec = decode(blob)
    v = view(blob)
    assert v.columns == list(dec.keys())
    for name in dec:
        assert v._col(name) == dec[name], f"coluna {name!r} divergiu view vs decode"


class TestBug02ViewParity:
    def test_view_drop_names_last_col_tcf_mode(self):
        # blob LEGÍTIMO do encoder: drop_names + última coluna em modo tcf
        # -> último token do meta é VAZIO. view crashava (IndexError); decode ok.
        table = {"a": [str(i) for i in range(20)], "b": list(VALS_TCF)}
        blob = encode(table, drop_names=True)
        meta = blob.split("\n", 1)[0][len("#TCF.8M") :]
        assert meta.split(",")[-1] == "", "pré-condição: último token vazio (modo tcf)"
        _parity(blob)

    def test_view_parity_escaped_names(self):
        table = {"a:b,c=d": ["x", "y"], "no\\me": ["p", "q"]}
        _parity(encode(table))

    def test_view_parity_mixed_modes(self):
        table = {
            "r": list(VALS_RAW * 34)[:100],
            "d": list(VALS_DICT),
            "t": ["constante-longa-repetida-x"] * 100,
        }
        _parity(encode(table))

    def test_view_parity_all_anonymous(self):
        table = {"a": ["1", "2", "3"], "b": ["x", "y", "z"]}
        _parity(encode(table, drop_names=True))


# ---------------------------------------------------------------------------
# BUG-07 — emitted_bytes/modo capturados no min(); body_bytes = candidato
# ---------------------------------------------------------------------------


def _body_slices(blob: str) -> list[int]:
    """Tamanho REAL do body de cada coluna, medido pelo header (fonte: formato)."""
    raw = blob.encode("utf-8")
    nl = raw.find(b"\n")
    meta = raw[:nl].decode("utf-8")[len("#TCF.8M") :]
    total_body = len(raw) - (nl + 1)
    sizes = []
    for tok in meta.split(","):
        if tok[:1] in "!@%":
            tok = tok[1:]
        if "=" in tok:
            sizes.append(int(tok.split("=", 1)[0], 16))
        else:
            sizes.append(None)  # última: até EOF
    consumed = sum(s for s in sizes if s is not None)
    return [s if s is not None else total_body - consumed for s in sizes]


class TestBug07EmittedBytes:
    TABLE = {"r": VALS_RAW, "d": [v[:1] for v in VALS_DICT][:3], "t": VALS_TCF[:3]}

    def _table(self):
        # 100 linhas pra estabilizar os modos: r->raw, d->dict, t->tcf
        return {
            "r": [f"u{i}x{i * 7}" for i in range(100)],  # únicos curtos -> raw
            "d": list(VALS_DICT),  # K=2 -> dict
            "t": ["constante-longa-repetida-x"] * 100,  # RLE -> tcf
        }

    def test_emitted_bytes_match_header_and_modes_exposed(self):
        side = SideOutputs()
        table = self._table()
        blob = encode(table, side_outputs=side)
        mi = side.multi_info
        # modo por coluna EXPOSTO (não só as listas raw/dict/split)
        assert mi["col_modes"]["d"] == "dict"
        assert mi["col_modes"]["t"] == "tcf"
        assert set(mi["col_modes"]) == set(table)
        # bytes EMITIDOS por coluna == medidos no próprio formato (header)
        sizes = _body_slices(blob)
        for (name, _), real in zip(table.items(), sizes):
            assert side.per_col[name].emitted_bytes == real, name
            assert side.per_col[name].emitted_mode == mi["col_modes"][name]
        assert sum(sizes) == mi["body_bytes"]

    def test_body_bytes_keeps_candidate_semantics(self):
        # na coluna onde raw/dict venceu, o candidato TCF é MAIOR que o emitido:
        # body_bytes (candidato/compute) != emitted_bytes (emitido) — semânticas distintas
        side = SideOutputs()
        encode(self._table(), side_outputs=side)
        for name in ("r", "d"):
            col = side.per_col[name]
            assert col.body_bytes is not None
            assert col.emitted_bytes < col.body_bytes, name
        t = side.per_col["t"]
        assert t.emitted_mode == "tcf" and t.emitted_bytes == t.body_bytes

    def test_parallel_telemetry_matches_serial(self):
        s1, s2 = SideOutputs(), SideOutputs()
        table = self._table()
        b1 = encode(table, side_outputs=s1)
        b2 = encode(table, side_outputs=s2, parallel=2)
        assert b1 == b2  # byte-identidade (já pinada alhures; pré-condição aqui)
        assert s1.multi_info["col_modes"] == s2.multi_info["col_modes"]
        for name in table:
            assert s1.per_col[name].emitted_bytes == s2.per_col[name].emitted_bytes


# ===========================================================================
# LOTE 2 (2026-07-10, decisões do owner): BUG-03/04/05/06
# ===========================================================================


class TestBug03ZeroRows:
    """0 linhas colide com 1-linha-vazia por construção (N valores = N-1
    separadores). Decisão: fail-loud AGORA; registro-'0' declarando schema fica
    pro trilho de armazenamento append/parquet/tcfx (registrado, ver ticket)."""

    def test_encode_empty_list_vira_flat(self):
        # CONTRATO ATUALIZADO (weld #2, canonicidade do vazio, owner 2026-07-24): `[]` vira a
        # forma FLAT `#TCF.8\n` (era `.8H` `#D0` no Passo 2). Nao fail-loud, representavel.
        # (Tabela 0-linha `{"a":[],"b":[]}` segue flat fail-loud — ver teste abaixo.)
        assert encode([]) == "#TCF.8\n"
        assert decode(encode([])) == []

    def test_dict_colunas_vazias_vira_8h(self):
        # CONTRATO ATUALIZADO (Passo 2): dict com TODAS as colunas vazias (0 linhas) deixa de
        # ser fail-loud e vira `.8H` OBJETO (campo = array vazio; o count `\0` E' coluna). O
        # flat 0-linha (irrepresentavel) so' se aplica a tabela COM ao menos 1 linha.
        assert encode({"a": [], "b": []}).startswith("#TCF.8H#O")
        assert decode(encode({"a": [], "b": []})) == {"a": [], "b": []}

    def test_single_empty_string_still_ok(self):
        # 1 linha vazia é DADO legítimo — não confundir com 0 linhas
        assert decode(encode([""])) == [""]
        assert decode(encode({"a": [""]})) == {"a": [""]}


class TestBug04UnknownVersion:
    """Versão é DEDUZÍVEL do próprio magic (#TCF.<dígitos>): != 8 -> fail-loud
    claro, não KeyError críptico do HCC. Subversões = controle de dev; compat
    real só no 1.0 (visão owner: '#TCF1M' fecha tudo — registrado)."""

    @pytest.mark.parametrize(
        "blob",
        [
            "#TCF.9M2=a,b\nxxyy",
            "#TCF.10M2=a,b\nxxyy",
            "#TCF.85M2=a,b\nxxyy",  # dígitos completos: versão 85, NÃO disc '5' do .8
            "#TCF.9\nqualquer",
        ],
    )
    def test_future_version_fails_loud(self, blob):
        with pytest.raises(ValueError, match="vers"):
            decode(blob)

    def test_legacy_67_keeps_git_hint(self):
        for legacy in ("#TCF.7 M\n# 2=a\nxx", "#TCF.6 M\n# 2=a\nxx"):
            with pytest.raises(ValueError, match="git checkout"):
                decode(legacy)

    def test_tcf8m_still_decodes(self):
        table = {"a": ["x", "y"], "b": ["1", "2"]}
        assert decode(encode(table)) == table

    def test_orphan_data_looking_like_prefix_survives_rt(self):
        vals = ["#TCF.x nao e versao", "linha norm"]
        assert decode(encode(vals)) == vals


class TestBug05Integrity:
    """O header JÁ declara os tamanhos; n_rows é invariante deduzível de graça.
    3 cheques decode-only: size, fecho do blob, cross-check n_rows.
    Limite conhecido (registrado): última coluna SEM size com excedente
    row-consistente é indetectável; view é lazy (sem cross-check n_rows)."""

    def _blob(self, **kw):
        return encode({"a": ["xx", "yy"], "b": ["pp", "qq"]}, **kw)

    def test_sized_col_truncated_raises(self):
        # size 0xff declarado, body só tem 5B -> truncamento deduzido do header
        with pytest.raises(ValueError, match="truncad"):
            decode("#TCF.8Mff=a,!b\nxx\nyy")

    def test_truncated_tail_raises_via_nrows(self):
        blob = self._blob()
        with pytest.raises(ValueError, match="diverg|truncad|n_rows"):
            decode(blob[:-4])

    def test_ragged_crafted_raises(self):
        # a declara 2 linhas, b tem 1 -> invariante n_rows quebrado
        with pytest.raises(ValueError, match="diverg|n_rows"):
            decode("#TCF.8M!5=a,!b\nxx\nyyp")

    def test_trailing_garbage_sized_last_raises(self):
        blob = self._blob(min_header=False)  # última COM size -> fecho checável
        with pytest.raises(ValueError, match="exced|sobra"):
            decode(blob + "LIXO")

    def test_view_sized_truncation_parity(self):
        with pytest.raises(ValueError, match="truncad"):
            view("#TCF.8Mff=a,!b\nxx\nyy")

    def test_intact_blobs_unaffected(self):
        for kw in ({}, {"min_header": False}, {"drop_names": True}):
            blob = self._blob(**kw)
            dec = decode(blob)
            assert list(dec.values()) == [["xx", "yy"], ["pp", "qq"]]


class TestBug06StringifyCheck:
    """Validar o que VAI SER USADO (pós _to_str), na MESMA passada que já
    stringifica — o guard prévio não via objetos cujo __str__ tem quebra."""

    def test_nonstr_custom_no_8h_fail_loud(self):
        # CONTRATO ATUALIZADO (Passo 2): coluna com valor NAO-str rota pro `.8H`; um objeto
        # custom (nao-JSON) falha alto na fronteira (tipo nao suportado) — antes o flat
        # stringificava e so' pegava o \n. (str-com-\n em valor .8H e' ESCAPADO, D_json.)
        class Sneaky:
            def __str__(self):
                return "linha1\nlinha2"

        with pytest.raises(Exception, match="suportado"):
            encode({"a": [Sneaky(), "v2"], "b": ["x", "y"]})

    def test_nonstr_cr_custom_no_8h_fail_loud(self):
        class SneakyCR:
            def __str__(self):
                return "l1\rl2"

        with pytest.raises(Exception, match="suportado"):
            encode({"a": [SneakyCR()], "b": ["x"]})

    def test_plain_str_newline_still_raises_both_branches(self):
        with pytest.raises(ValueError, match="quebra de linha"):
            encode({"a": ["x\ny"]})
        with pytest.raises(ValueError, match="quebra de linha"):
            encode(["x\ny"])


# ===========================================================================
# LOTE 3 (2026-07-10, decisões do owner): BUG-08 fold + BUG-09 + BUG-10 + BUG-11b
# Fronteiras = ISOLAMENTO ("o código tendo tratamento pode identificar eles e a
# gente pode mudar comportamento") — revisão profunda pré-1.0 em ticket próprio.
# ===========================================================================


class TestLote3ApiBoundaries:
    """BUG-09 + BUG-10: fronteiras da API fail-loud/consistentes."""

    def test_str_como_valor_de_coluna_vira_8h_objeto(self):  # BUG-09 (contrato atualizado)
        # CONTRATO ATUALIZADO (Passo 2): dict com valor str (nao-lista) vira `.8H` OBJETO
        # (campo = str), nao mais TypeError. decode devolve a mesma estrutura.
        assert encode({"a": "xyz"}).startswith("#TCF.8H#O")
        assert decode(encode({"a": "xyz"})) == {"a": "xyz"}

    def test_bytes_como_valor_no_8h_fail_loud(self):  # BUG-09 (contrato atualizado)
        # bytes nao e' tipo JSON -> rota .8H -> fail-loud (tipo nao suportado).
        with pytest.raises(Exception, match="suportado"):
            encode({"a": b"xyz"})

    def test_list_nonstr_vira_8h_tipado(self):  # BUG-10a (contrato atualizado)
        # CONTRATO ATUALIZADO (Passo 2, type-coherent): list nao-str vira `.8H`. Array UNIFORME
        # tipado PRESERVA o tipo (fim da perda-de-tipo silenciosa); array de tipos MISTOS (union
        # int+null+str) e' fail-loud — fora do .8H (P5), ensina a converter/separar.
        assert decode(encode([1, 2, 3])) == [1, 2, 3]              # int uniforme: tipo preservado
        with pytest.raises(Exception, match="MISTOS|suportado"):
            encode([1, None, "x"])                                 # tipos mistos = union P5

    def test_list_custom_nao_json_fail_loud(self):  # BUG-10a×06 (contrato atualizado)
        class Sneaky:
            def __str__(self):
                return "a\nb"

        with pytest.raises(Exception, match="suportado"):
            encode([Sneaky()])

    def test_layers_wrong_type_raises(self):  # BUG-10b
        with pytest.raises(TypeError, match="PipelineConfig"):
            encode(["a", "b"], layers={"pre_pass": False})

    def test_parallel_negative_raises(self):  # BUG-10c
        with pytest.raises(ValueError, match="parallel"):
            encode({"a": ["1", "2"], "b": ["x", "y"]}, parallel=-2)

    def test_parallel_one_is_serial_no_pool(self):  # BUG-10c
        side = SideOutputs()
        table = {"a": ["1", "2"], "b": ["x", "y"]}
        blob = encode(table, parallel=1, side_outputs=side)
        assert side.multi_info["parallel_workers"] == 0  # dedução: 1 worker ≡ serial
        assert blob == encode(table)  # byte-idêntico

    def test_parallel_true_still_parallel(self):  # guarda (True==1 em Python!)
        side = SideOutputs()
        table = {"a": ["1", "2"], "b": ["x", "y"], "c": ["p", "q"]}
        blob = encode(table, parallel=True, side_outputs=side)
        assert side.multi_info["parallel_workers"] >= 2
        assert blob == encode(table)

    def test_decode_nonstr_raises_typeerror(self):  # BUG-10d
        with pytest.raises(TypeError, match="str"):
            decode(123)

    def test_name_without_nature_raises(self):  # BUG-10e
        with pytest.raises(ValueError, match="nature"):
            encode(["a", "b"], name="col")

    def test_nature_with_dict_raises(self):  # BUG-10g
        from tcf import SPEC_CPF

        with pytest.raises(ValueError, match="nature_per_col"):
            encode({"a": ["111.444.777-35"]}, nature=SPEC_CPF)

    def test_nature_per_col_with_list_raises(self):  # BUG-10g
        from tcf import SPEC_CPF

        with pytest.raises(ValueError, match="nature="):
            encode(["111.444.777-35"], nature_per_col={"a": SPEC_CPF})


class TestNatureIgnoradaCalada:
    """T-NATURE-IGNORADA-CALADA situações (1) e (2) — o usuário pede spec e recebe
    outra coisa SEM AVISO (fechadas 2026-08-16, item C3 da fila do M).

    (1) `nature_per_col` numa lista TIPADA (ou vazia) era aceito e DESCARTADO: o
        rejeitador de BUG-10g estava condicionado a `_lista_flat`, FALSO para
        `[1,2,3]`. `list[dict]` (dataset .8H) continua ACEITANDO — é a rota de
        nature hierárquica, e ela aplica de verdade (medido: 799 -> 52 B).
    (2) coluna INEXISTENTE no `nature_per_col` do multi-col era filtrada calada
        (`if name in data`). O `.8H` JÁ falhava alto em path inexistente — o
        `.8M` é que estava fora do padrão.
    """

    def test_1_lista_tipada_rejeita(self):
        from tcf.natures import SPEC_DATA_ISO

        for tipada in ([738886, 738887], [1.5, 2.5], [True, False]):
            with pytest.raises(ValueError, match="nature="):
                encode(tipada, nature_per_col={"d": SPEC_DATA_ISO})

    def test_1_lista_vazia_rejeita(self):
        from tcf.natures import SPEC_DATA_ISO

        with pytest.raises(ValueError, match="nature="):
            encode([], nature_per_col={"d": SPEC_DATA_ISO})

    def test_1_list_of_dict_continua_aceitando(self):
        # contra-prova: a rota de nature HIERÁRQUICA não pode ser afetada
        from tcf.natures import SPEC_DATA_ISO

        recs = [{"d": f"2015-{m:02d}-01"} for m in range(1, 13)]
        blob = encode(recs, nature_per_col={"d": SPEC_DATA_ISO})
        assert decode(blob) == recs

    def test_2_coluna_inexistente_rejeita(self):
        from tcf.natures import SPEC_DATA_ISO

        tabela = {"d": ["2024-01-01", "2024-01-02"], "s": ["a", "b"]}
        with pytest.raises(ValueError, match="ZZZ"):
            encode(tabela, nature_per_col={"ZZZ": SPEC_DATA_ISO})
        # e também quando vem MISTURADA com uma coluna válida
        with pytest.raises(ValueError, match="ZZZ"):
            encode(tabela, nature_per_col={"d": SPEC_DATA_ISO, "ZZZ": SPEC_DATA_ISO})

    def test_2_slot_none_continua_valido(self):
        # contra-prova: `{col: None}` = coluna sem nature é contrato PRÉ-EXISTENTE
        tabela = {"d": ["2024-01-01", "2024-01-02"]}
        assert decode(encode(tabela, nature_per_col={"d": None})) == tabela

    def test_2_coluna_existente_continua_aplicando(self):
        from tcf.natures import SPEC_DATA_ISO
        from tcf.side_outputs import SideOutputs

        datas = [f"2015-{m:02d}-01" for m in range(1, 13)]
        side = SideOutputs()
        tabela = {"d": datas, "s": ["x"] * 12}
        blob = encode(tabela, nature_per_col={"d": SPEC_DATA_ISO}, side_outputs=side)
        assert decode(blob) == tabela
        assert side.nature_apply["d"]["apply_rate"] == 1.0


class TestLote3FreezeAssimetrias:
    """PASSADA DE CONGELAMENTO 2026-07-17 (T-API-BOUNDARY-CONTRACTS, gate .8).

    3 assimetrias MEDIDAS que estavam sem pino. Decisão do owner: **MANTER** (nenhuma é
    corrupção — o contrato flat está congelado, ADR-0024). Estes testes CONGELAM o
    comportamento atual; melhorias de ergonomia ficam registradas como follow-up pré-1.0.
    """

    def test_tuple_como_valor_de_coluna_fail_loud(self):
        # CONTRATO ATUALIZADO (Passo 2): tuple NAO e' list -> nao e' tabela flat -> rota `.8H`,
        # e tuple nao e' tipo JSON -> fail-loud (era: convertia p/ list silenciosamente).
        with pytest.raises(Exception, match="suportado"):
            encode({"a": ("x", "y")})

    def test_tuple_no_topo_fail_loud(self):
        # CONTRATO ATUALIZADO (Passo 2): tuple no topo -> rota `.8H` (envelope #V) -> tipo nao
        # suportado (fail-loud claro, nao stringifica).
        with pytest.raises(Exception, match="suportado"):
            encode(("a", "b"))

    def test_decode_nature_per_col_em_single_ignorado_sem_corromper(self):
        # decode(single-col, nature_per_col=) IGNORA o kwarg (single usa nature=, não _per_col).
        # NÃO corrompe (mesma saída); a re-tipagem/alinhamento é follow-up pré-1.0.
        w = encode(["a", "b"])
        assert decode(w, nature_per_col={"z": None}) == decode(w) == ["a", "b"]

    def test_parallel_true_em_single_col_serial_silencioso(self):
        # single-col não tem pool: parallel=True é serial silencioso (byte-idêntico).
        assert encode(["a", "b"], parallel=True) == encode(["a", "b"])


class TestLote3MetaStrict:
    """BUG-11b whitelist de escape + BUG-08 dobrado (não-emitível = erro)."""

    def test_escape_of_nonstructural_char_is_error(self):  # BUG-11b
        # encoder só escapa ,=:\ e !@% inicial; '\b' é não-emitível -> corrupção
        with pytest.raises(ValueError, match="corromp|escape"):
            decode("#TCF.8M2=a\\bc,!z\nXXYY")

    def test_legit_escapes_still_roundtrip(self):
        table = {
            "a,b": ["x", "y"],
            "c=d": ["p", "q"],
            "e:f": ["1", "2"],
            "g\\h": ["u", "v"],
            "!bang": ["m", "n"],
        }
        assert decode(encode(table)) == table

    def test_empty_meta_empty_body_is_error(self):  # BUG-08 fold
        # '#TCF.8M\n' (meta vazio E body vazio) é não-emitível: 0-rows rejeitado
        # no encode e 1-linha-vazia sempre gera >=1 byte de body ou marcador '!'
        with pytest.raises(ValueError, match="vazio|corromp"):
            decode("#TCF.8M\n")
        with pytest.raises(ValueError, match="vazio|corromp"):
            view("#TCF.8M\n")

    def test_empty_meta_with_body_still_legit(self):
        # achado da verificação: meta vazio COM body é blob legítimo do encoder
        blob = encode({"a": ["constante-longa-x"] * 5}, drop_names=True)
        assert blob.startswith("#TCF.8M\n")
        assert decode(blob) == {"0": ["constante-longa-x"] * 5}
        v = view(blob)
        assert v._col("0") == ["constante-longa-x"] * 5


# ===========================================================================
# LOTE 4 (2026-07-10, "vamos fechar os A"): BUG-13 b/d/e — decode estrito fino
# ===========================================================================


class TestLote4NatureIdStrict:
    """BUG-13b: nature-id desconhecido no header = ERRO (revoga o contrato
    forward-compat de 2026-06-24 — decisão owner 2026-07-10: pre-1.0 não tem
    forward-compat a proteger, ADR-0024; seguir com dado cru base-94 calado é
    corrupção silenciosa)."""

    def _tampered_multi(self):
        from tcf import SPEC_CNPJ

        text = encode(
            {"doc": ["11.222.333/0001-81"], "x": ["a"]},
            nature_per_col={"doc": SPEC_CNPJ},
        )
        return text.replace(":cnpj", ":zzz")

    def test_unknown_nature_id_multi_raises(self):
        with pytest.raises(ValueError, match="desconhecido"):
            decode(self._tampered_multi())

    def test_unknown_nature_id_single_raises(self):
        from tcf import SPEC_CPF

        text = encode(["529.982.247-25", "111.444.777-35"], nature=SPEC_CPF)
        with pytest.raises(ValueError, match="desconhecido"):
            decode(text.replace(":cpf", ":zzz", 1))

    def test_unknown_nature_id_view_raises_on_materialize(self):
        v = view(self._tampered_multi())  # parse lazy passa; erro ao materializar
        with pytest.raises(ValueError, match="desconhecido"):
            v._col("doc")


class TestLote4ViewIncremental:
    """BUG-13d: cross-check de n_rows INCREMENTAL na materialização da view —
    compara len ao materializar a 2ª coluna (ints, custo zero, laziness intacta)."""

    def test_view_incremental_nrows_check(self):
        blob = encode({"a": ["xx", "yy"], "b": ["pp", "qq"]})
        v = view(blob[:-4])  # última col (EOF) truncada: parse lazy passa
        assert v._col("a") == ["xx", "yy"]
        with pytest.raises(ValueError, match="diverg|n_rows"):
            v._col("b")  # materializa 1 row vs 2 -> incremental pega

    def test_view_consistent_columns_unaffected(self):
        blob = encode({"a": ["xx", "yy"], "b": ["pp", "qq"]})
        v = view(blob)
        assert v._col("a") == ["xx", "yy"] and v._col("b") == ["pp", "qq"]


class TestLote4InternalInvariants:
    """BUG-13e: invariantes internas dos slots deduzidas de graça — erro CLARO
    em vez de IndexError críptico / dado errado."""

    def test_v2b_trailing_byte_raises_clear(self):
        # última coluna '@' EOF + '\n' de editor: antes IndexError 'list index
        # out of range' (byte 0x0A vira índice negativo no stream base-94)
        table = {
            "grp": [f"g{i % 3}" for i in range(30)],
            "txt": [
                f"linha de texto {i % 10} com recheio comum bem longo"
                for i in range(30)
            ],
        }
        blob = encode(table)
        meta = blob.split("\n", 1)[0]
        assert (
            meta.rstrip("abgrptx=0123456789").endswith("@") or "@" in meta
        )  # há coluna dict
        with pytest.raises(ValueError, match="V2-B"):
            decode(blob + "\n")

    def test_v2b_table_truncated_raises(self):
        from tcf.multi import _decode_v2b

        with pytest.raises(ValueError, match="V2-B"):
            _decode_v2b(b"99\nab!!")  # ntable 99 > bytes disponiveis

    def test_split_template_truncated_raises(self):
        from tcf.multi import _decode_struct_split

        with pytest.raises(ValueError, match="split"):
            _decode_struct_split(b"999\nxx")  # ntmpl 999 > bytes disponiveis


# ---------------------------------------------------------------------------
# ADR-0046 — nome VAZIO '' é nome (sai `\z`), preservado; anônima SÓ via drop_names
# ---------------------------------------------------------------------------


class TestNomeVazioPreservadoADR0046:
    """Fecha o BUG-CHAVE-VAZIA-POSICIONAL — o único caso em que o TCF ALTERAVA o dado.

    A causa era uma COLISÃO de grafia: `encode({"": [...]})` produzia o MESMO wire que
    `encode({"x": [...]}, drop_names=True)`. O `.8H` já resolvia com o sentinela `\z`
    (ADR-0033, 2026-07-17); a convenção foi portada de volta ao `.8M` (ADR-0046).
    """

    def test_posicoes(self):
        for table in ({"": ["1"], "b": ["2"]}, {"a": ["1"], "": ["2"], "c": ["3"]},
                      {"a": ["1"], "": ["2"]}, {"": ["a", "b"]}):
            blob = encode(table)
            assert decode(blob) == table, table
            _parity(blob)

    def test_nature_per_col_na_coluna_vazia(self):
        from tcf import SPEC_CPF

        table = {"": ["529.982.247-25", "111.444.777-35"]}
        blob = encode(table, nature_per_col={"": SPEC_CPF})
        assert blob.split("\n", 1)[0] == "#TCF.8M!\\z:cpf"
        assert decode(blob) == table

    def test_nome_literal_backslash_z_e_vazio_juntos(self):
        table = {"": ["1"], "\\z": ["2"]}
        blob = encode(table)
        assert decode(blob) == table          # `\z` vs `\\z`: injetivo

    def test_wire_antigo_anonimo_continua_decodando_posicional(self):
        # o wire que o encoder PRÉ-0046 emitia para {"": ...} é indistinguível de
        # drop_names — e continua decodando como posicional (tolerante, nada quebra).
        assert decode("#TCF.8M!\na\nb") == {"0": ["a", "b"]}

    def test_corrupcao_continua_fail_loud(self):
        with pytest.raises(ValueError, match="DECLARADO vazio|corromp"):
            decode("#TCF.8M!1=\nx")                 # '<size>=' com token CRU vazio
        with pytest.raises(ValueError, match="nao-estrutural|corromp"):
            decode("#TCF.8M!a\\zb\nx")              # `\z` EMBUTIDO no nome

    def test_csv_rfc4180_com_header_vazio_faz_roundtrip(self):
        # o nome vazio nasce do próprio CSV: campo vazio é legal (RFC 4180)
        import csv
        import io

        for texto in ("a,b,\n1,2,3\n", "a,,b\n1,2,3\n", ",a,b\n0,1,2\n"):
            r = csv.reader(io.StringIO(texto))
            h = next(r)
            cols = {k: [] for k in h}
            for row in r:
                for k, v in zip(h, row):
                    cols[k].append(v)
            assert decode(encode(cols)) == cols, texto

    def test_view_ve_a_coluna_vazia(self):
        v = view(encode({"": ["1", "2"], "b": ["3", "4"]}))
        assert v.columns == ["", "b"]
        assert v.select([""]) == [{"": "1"}, {"": "2"}]
