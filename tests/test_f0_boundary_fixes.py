"""T-QA-8 F0 lote 1 — repros pinados dos BUG-01/02/07 (red->green, 2026-07-10).

Decisões do owner (2026-07-10):
- BUG-01: coluna com nome '' = coluna SEM nome (anônima) — a entrada é TRANSFORMADA
  na fronteira (warning), o meta NUNCA emite escape-vazio; no decode, escape/declaração
  de nome vazio = ERRO (marcador de corrupção; futuro reparador em ticket próprio).
- BUG-02: paridade view vs decode por CONSTRUÇÃO (parser único do meta), não por
  verificação extra.
- BUG-07: `body_bytes` MANTÉM a semântica de candidato TCF (custo de compute/memória —
  telemetria válida nesse sentido); os bytes REALMENTE emitidos + modo vencedor são
  capturados NO PONTO do min() (contagem já existente pro header — zero passada extra).
"""
from __future__ import annotations

import pytest

from tcf import decode, encode, view
from tcf.side_outputs import SideOutputs

# Colunas de controle com modo PREVISÍVEL no min(tcf, raw, dict, split):
VALS_RAW = ["q", "w", "e"]                      # curtas/únicas -> raw vence
VALS_DICT = ["alpha", "beta"] * 50              # K=2, N=100 -> dict vence
VALS_TCF = ["constante-longa-repetida-x"] * 20  # RLE *20| -> tcf vence


# ---------------------------------------------------------------------------
# BUG-01 — nome de coluna vazio '' (encode: transforma; decode: fail-loud)
# ---------------------------------------------------------------------------

class TestBug01EmptyColName:
    def test_empty_name_becomes_anonymous_with_warning(self):
        table = {"": ["x", "y"], "b": ["p", "q"]}
        with pytest.warns(UserWarning, match="anonima|anônima|posicional"):
            blob = encode(table)
        dec = decode(blob)
        # coluna '' vira anônima -> decode dá o nome POSICIONAL ('0'); NADA se perde
        assert dec == {"0": ["x", "y"], "b": ["p", "q"]}

    def test_empty_name_single_column_table(self):
        with pytest.warns(UserWarning):
            blob = encode({"": ["a", "b"]})
        assert decode(blob) == {"0": ["a", "b"]}

    def test_empty_name_meta_has_no_escape(self):
        # a transformação EVITA o escape: nenhum '\' no meta
        with pytest.warns(UserWarning):
            blob = encode({"": ["x", "y"], "b": ["p", "q"]})
        meta = blob.split("\n", 1)[0]
        assert "\\" not in meta

    def test_empty_name_positional_collision_fails_loud(self):
        # '' na posição 0 viraria '0' no decode — colide com a coluna real '0'
        with pytest.raises(ValueError, match="posicional|colid"):
            encode({"": ["x"], "0": ["y"]})

    def test_decode_escaped_dangling_backslash_is_error(self):
        # nome terminando em backslash SOLTO (cauda ímpar = escape de nada): o
        # encoder nunca emite ('\' legítimo sai '\\', cauda par) -> corrupção.
        # Obs: '\,' NÃO é erro (vírgula escapada legítima de um nome com ',').
        corrupt = "#TCF.8M!1=b,a\\\nxy"           # último token: 'a\' (dangling)
        with pytest.raises(ValueError, match="corromp|dangling|solto"):
            decode(corrupt)

    def test_decode_declared_empty_name_is_error(self):
        # '<size>=' (nome DECLARADO mas vazio): encoder nunca emite -> corrupção
        corrupt = "#TCF.8M1=,!b\nxy"
        with pytest.raises(ValueError, match="corrup|vazio"):
            decode(corrupt)


class TestAnonLastColGrammar:
    """Achado da verificação adversarial F0 (2026-07-10): '<size>' bare no ÚLTIMO
    token é ambíguo com NOME (0xc parsearia como coluna 'c') -> última anônima
    emite SEMPRE sem size, inclusive com min_header=False."""

    def test_min_header_false_empty_name_last_no_key_corruption(self):
        # repro do refutador: size hex da anônima colidia com o nome 'c' e a
        # tabela decodava com UMA coluna só (dados perdidos)
        table = {"c": ["k1", "k2", "k3", "k4"], "": ["abc", "de", "fg", "hi"]}
        with pytest.warns(UserWarning):
            blob = encode(table, min_header=False)
        assert decode(blob) == {"c": ["k1", "k2", "k3", "k4"],
                                "1": ["abc", "de", "fg", "hi"]}
        _parity(blob)

    def test_min_header_false_drop_names_all_positional(self):
        vals = [f"item_{i:03d}_end" for i in range(4)]
        table = {"a": vals, "b": ["1", "2", "3", "4"], "c": vals}
        blob = encode(table, drop_names=True, min_header=False)
        assert list(decode(blob).keys()) == ["0", "1", "2"]
        _parity(blob)

    def test_empty_name_with_drop_names_has_no_false_collision(self):
        # com drop_names TODAS decodam posicionais — '1' de entrada não colide
        with pytest.warns(UserWarning):
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
        meta = blob.split("\n", 1)[0][len("#TCF.8M"):]
        assert meta.split(",")[-1] == "", "pré-condição: último token vazio (modo tcf)"
        _parity(blob)

    def test_view_parity_escaped_names(self):
        table = {"a:b,c=d": ["x", "y"], "no\\me": ["p", "q"]}
        _parity(encode(table))

    def test_view_parity_mixed_modes(self):
        table = {"r": list(VALS_RAW * 34)[:100], "d": list(VALS_DICT),
                 "t": ["constante-longa-repetida-x"] * 100}
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
    meta = raw[:nl].decode("utf-8")[len("#TCF.8M"):]
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
            "r": [f"u{i}x{i * 7}" for i in range(100)],   # únicos curtos -> raw
            "d": list(VALS_DICT),                          # K=2 -> dict
            "t": ["constante-longa-repetida-x"] * 100,     # RLE -> tcf
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
            assert (s1.per_col[name].emitted_bytes
                    == s2.per_col[name].emitted_bytes)
