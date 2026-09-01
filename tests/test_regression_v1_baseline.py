"""Suite de regressao byte-canonical pra v1.0 baseline.

Snapshot byte-count + RT pra datasets-chave. Qualquer mudanca em
src/tcf/ que mude um byte aqui = regressao. Bytes documentados em:

    experiments/lab/dirty/2026-05/2026-05-27/2026-05-27-baseline-consolidado/METRICS.md

Estrategia (Beizer 1995 — characteristic outputs):
- D1-D9: 9 datasets sinteticos single-col (M10 baseline + header = 1545B total)
- D17a: 1 dataset sintetico multi-col (300B INVARIANT, #TCF.8M hex — ADR-0032 default)

Regressao byte-canonical REAL-WORLD (colunas free-text, regime
n_tam_est>=3) vive em test_real_world_snapshots.py — fixtures committadas
em datasets/samples/ (frozen, portaveis, NAO dependem de Z:). Gate
obrigatorio pra mudancas em HCC/prune.
"""

from __future__ import annotations

import csv
import inspect
from pathlib import Path

import pytest

import tcf
from tcf import encode, decode


ROOT = Path(__file__).resolve().parent.parent
DATASETS = ROOT / "datasets" / "synthetic"


# Superficie de API publica. Sob ADR-0024/0028 (pre-1.0) a adicao e' ADITIVA —
# atualizar esta lista ao exportar algo novo. Bump de versao (0.7.1 -> 0.8.0,
# #TCF.8 vira default; ADR-0032/0028) acontece no release, nao a cada export.
EXPECTED_PUBLIC_API = {
    "encode",
    "decode",
    "SideOutputs",
    "build_schema",
    "TableSchema",
    "ColumnSchema",
    "TemplatedCheckedSpec",
    "TemplatedPaddedSpec",
    "SPEC_CPF",
    "SPEC_CNPJ",
    "SPEC_IP",
    # o registry name->spec e' a fonte do `schema=` por string (ADR-0047).
    "SPEC_DATA_ISO",
    "SPEC_INT_PAD",
    "SPEC_REGISTRY",
    "PipelineConfig",
    "view",       # camada read-only lazy/consultavel (A4, plano 0.8)
    "LazyTCF",    # A4
    "Filtered",   # A4
    # encode_hierarchical REMOVIDO do publico (Passo 2, API unica 2026-07-23): encode() rota
    # entrada aninhada pro .8H; o dev usa so' encode/decode (simetrico ao decode).
    # encode_table/decode_table APOSENTADOS 2026-06-24 (T-CODE-LEGACY-PRUNE-PRE-07)
}


class TestPublicAPISurface:
    """ADR-0017: API publica congelada. Contrato enforced por test."""

    def test_all_matches_expected(self):
        assert set(tcf.__all__) == EXPECTED_PUBLIC_API, (
            "tcf.__all__ divergiu da API publica congelada (ADR-0017). "
            "Adicionar/remover export requer atualizar EXPECTED_PUBLIC_API + "
            "bump de versao + nota no ADR.\n"
            f"  faltando: {EXPECTED_PUBLIC_API - set(tcf.__all__)}\n"
            f"  extra:    {set(tcf.__all__) - EXPECTED_PUBLIC_API}"
        )

    def test_all_symbols_importable(self):
        """Cada nome em __all__ deve existir como atributo do modulo."""
        for name in tcf.__all__:
            assert hasattr(tcf, name), f"tcf.__all__ lista '{name}' mas nao existe"

    def test_version_pre_1_0(self):
        # Pré-1.0 (ADR-0024): pacote em 0.x, minor acompanha o formato
        # (#TCF.8 -> 0.8.x, ADR-0032/0028); patch e' livre pra fixes sem
        # mudanca de emissao. PyPI publica no go do owner.
        #
        # 0.8.4 (2026-09-01): a grafia da entrada deixa de escolher o arsenal. O patch
        # subiu com DUAS mudancas de emissao, e o minor NAO, porque o FORMATO continua
        # `#TCF.8` e e' ele que governa o minor: o `R` do ADR-0049 e' um discriminador
        # NOVO dentro da mesma era, do mesmo jeito que o `H` e o `B` foram, e o FLOOR do
        # `sort_by` (ADR-0050) muda o que se escolhe emitir, nao a gramatica do wire.
        # Os gates byte-canonicos (D1-D9, D17a, real-world) nao re-pinaram: nenhum deles
        # usa lista de registros nem `sort_by`.
        assert tcf.__version__ == "0.8.4"

    # CONGELAMENTO DO .8 ("terminar o .8 com as formalidades e
    # congelar parametros, header e corpo"). Este pin e' o "congelar PARAMETROS"
    # como artefato executavel — nome, ordem, kind e default de cada parametro
    # das duas portas. Header e corpo ja' estao pinados pelos gates
    # byte-canonicos (D1-D9/D17a/real-world) + spec docs/algorithms/TCF-format.
    # Mudar assinatura = re-pin DELIBERADO aqui + registro (ADR/vigencia).
    ENCODE_SIGNATURE_FROZEN = [
        ("data", "POSITIONAL_OR_KEYWORD", inspect.Parameter.empty),
        ("schema", "KEYWORD_ONLY", None),          # ADR-0047 (parametro unico de spec)
        ("side_outputs", "KEYWORD_ONLY", None),
        ("parallel", "KEYWORD_ONLY", False),
        ("layers", "KEYWORD_ONLY", None),
        ("fallback", "KEYWORD_ONLY", True),
        ("min_header", "KEYWORD_ONLY", True),
        ("min_len", "KEYWORD_ONLY", None),
        ("sort_by", "KEYWORD_ONLY", None),
        ("name", "KEYWORD_ONLY", None),
        ("stamp", "KEYWORD_ONLY", None),
        ("drop_names", "KEYWORD_ONLY", False),
    ]
    DECODE_SIGNATURE_FROZEN = [
        ("tcf_text", "POSITIONAL_OR_KEYWORD", inspect.Parameter.empty),
        ("schema", "KEYWORD_ONLY", None),          # ADR-0047, simetrico ao encode
        ("max_length", "KEYWORD_ONLY", None),
    ]

    @pytest.mark.parametrize("fn_name,frozen", [
        ("encode", ENCODE_SIGNATURE_FROZEN),
        ("decode", DECODE_SIGNATURE_FROZEN),
    ])
    def test_assinatura_publica_congelada(self, fn_name, frozen):
        atual = [
            (p.name, p.kind.name, p.default)
            for p in inspect.signature(getattr(tcf, fn_name)).parameters.values()
        ]
        assert atual == frozen, (
            f"assinatura de tcf.{fn_name} divergiu do congelamento do .8. "
            f"Mudanca de parametro exige re-pin deliberado + "
            f"registro.\n  congelada: {frozen}\n  atual:     {atual}"
        )


# ADR-0034, git-as-compat ADR-0024: o header `#TCF.8` + LF passou a
# ser DEFAULT no single-col -> +7 B EXATOS por dataset. NAO e' regressao de compressao:
# o core nao mudou 1 byte, so' o header entrou. Valores anteriores vivem no git.
D1_D9_BYTES_FROZEN = {
    "D1-emails-simples":    125,
    "D2-emails-quote-id":   173,
    "D3-stress-substring":  184,
    "D4-caos-mix":          120,
    "D5-padroes-multiplos": 267,
    "D6-poucos-em-ruido":   274,
    "D7-aninhamento":       222,
    "D8-cabeca-cauda":      107,
    "D9-frequencia-alta":    73,
}

D1_D9_TOTAL = 1545  # sum acima. 1523 -> 1586 (+63 = 9 x 7 B de header, ADR-0034)
                    # -> 1545 (-41 em D5/D6, delimitador de POLARIDADE 2026-07-26:
                    # 1 byte por TRANSICAO em vez de 1 por LITERAL; FLOOR nunca-pior,
                    # por isso os outros 7 nao mexeram). Re-pinavel (ADR-0024).

D17A_INVARIANT = 300  # #TCF.8M default (ADR-0032): era 307 (sem V2-B) -> 303 (V2-B
                      # decimal) -> 302 (V2-B hex #TCF.7) -> 300 (#TCF.8M hex inline,
                      # header -2B vs #TCF.7). Re-pinavel (ADR-0024/0025). Legado
                      # #TCF.6/.7 CORTADO (git-as-compat).


def _load_single_col(name: str) -> list[str]:
    with (DATASETS / f"{name}.csv").open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def _load_multi_col(name: str) -> dict[str, list[str]]:
    with (DATASETS / f"{name}.csv").open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


class TestD1D9ByteCanonical:
    """D1-D9 cada um com snapshot frozen."""

    @pytest.mark.parametrize("name,expected_bytes", list(D1_D9_BYTES_FROZEN.items()))
    def test_byte_count_matches_snapshot(self, name, expected_bytes):
        values = _load_single_col(name)
        text = encode(values)
        actual = len(text.encode("utf-8"))
        assert actual == expected_bytes, (
            f"{name}: esperado {expected_bytes}B, obteve {actual}B "
            f"(regressao byte-canonical — atualizar snapshot OU investigar src/tcf)"
        )

    @pytest.mark.parametrize("name", list(D1_D9_BYTES_FROZEN.keys()))
    def test_round_trip(self, name):
        values = _load_single_col(name)
        text = encode(values)
        assert decode(text) == values, f"RT broken em {name}"

    def test_d1_d9_total_invariant(self):
        """Total D1-D9 = 1545B (ADR-0034)."""
        total = 0
        for name in D1_D9_BYTES_FROZEN:
            values = _load_single_col(name)
            text = encode(values)
            total += len(text.encode("utf-8"))
        assert total == D1_D9_TOTAL, (
            f"D1-D9 total mudou: esperado {D1_D9_TOTAL}B, obteve {total}B"
        )


class TestD17AInvariant:
    """D17a multi-col baseline: #TCF.8M default = 300B (V2-B na coluna `categoria`,
    hex, ADR-0032). Baseline = guarda de regressao re-pinavel em mudanca INTENCIONAL
    (ADR-0024/0025), nao contrato eterno."""

    def test_d17a_exact_baseline(self):
        cols = _load_multi_col("D17a-multi-column-mixed")
        text = encode(cols)
        actual = len(text.encode("utf-8"))
        assert actual == D17A_INVARIANT, (
            f"D17a baseline (300B, #TCF.8M) mudou: obteve {actual}B. Re-pina so' se a "
            f"mudanca de formato for INTENCIONAL (ADR-0024/0025)."
        )

    def test_d17a_round_trip(self):
        cols = _load_multi_col("D17a-multi-column-mixed")
        text = encode(cols)
        assert decode(text) == cols
